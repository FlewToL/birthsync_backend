import asyncio
import calendar
import html
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import asyncpg
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from app.core.config import settings
from app.db.context import db_connection, db_transaction


@dataclass(frozen=True)
class ReminderNotification:
    reminder_id: UUID
    user_id: int
    contact_id: int
    telegram_id: int
    contact_name: str
    title: str
    description: str | None
    notification_type: str
    notification_key: str
    occurrence_at: datetime
    scheduled_at: datetime


def _create_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        await message.answer(
            "BirthSync подключен. Теперь я смогу присылать напоминания о предстоящих событиях."
        )

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(
            "Я отправляю уведомления по напоминаниям из BirthSync. "
            "Создавай события в мини-приложении, а я напомню о них в Telegram."
        )

    return router


class TelegramBotService:
    def __init__(self) -> None:
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None
        self._polling_task: asyncio.Task[None] | None = None
        self._reminder_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        token = self._get_token()
        if token is None:
            logger.info("TELEGRAM_BOT_TOKEN is not configured; Telegram bot integration is disabled")
            return

        self._stop_event = asyncio.Event()
        self._bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        try:
            bot_info = await self._bot.get_me()
        except Exception as exc:
            logger.exception(f"Failed to initialize Telegram bot: {exc}")
            await self._bot.session.close()
            self._bot = None
            return

        logger.success(f"Telegram bot initialized as @{bot_info.username}")

        if settings.telegram_reminders_enabled:
            self._reminder_task = asyncio.create_task(
                self._run_reminder_worker(),
                name="telegram-reminder-worker",
            )
            logger.info("Telegram reminder worker started")

        if settings.telegram_bot_polling_enabled:
            self._dispatcher = Dispatcher()
            self._dispatcher.include_router(_create_router())
            self._polling_task = asyncio.create_task(
                self._dispatcher.start_polling(self._bot, handle_signals=False),
                name="telegram-bot-polling",
            )
            logger.info("Telegram bot polling started")

    async def stop(self) -> None:
        self._stop_event.set()

        if self._dispatcher is not None:
            with suppress(Exception):
                await self._dispatcher.stop_polling()

        tasks = [task for task in (self._reminder_task, self._polling_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if self._bot is not None:
            await self._bot.session.close()

        self._bot = None
        self._dispatcher = None
        self._polling_task = None
        self._reminder_task = None
        logger.info("Telegram bot integration stopped")

    async def _run_reminder_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._process_due_reminders()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception(f"Telegram reminder worker failed: {exc}")

            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=settings.telegram_reminder_poll_interval_seconds,
                )

    async def _process_due_reminders(self) -> None:
        if self._bot is None:
            return

        timezone = self._get_timezone()
        now = datetime.now(timezone)
        window_start = now - timedelta(minutes=settings.telegram_reminder_late_grace_minutes)
        reminders = await self._fetch_active_reminders()
        notifications: list[ReminderNotification] = []

        for reminder in reminders:
            notifications.extend(self._build_notifications(reminder, now, window_start, timezone))

        if not notifications:
            return

        notifications.sort(key=lambda item: item.scheduled_at)
        logger.info(f"Found {len(notifications)} due Telegram reminder notification(s)")

        for notification in notifications:
            notification_id = await self._claim_notification(notification)
            if notification_id is None:
                continue
            await self._send_notification(notification_id, notification)

    async def _send_notification(self, notification_id: int, notification: ReminderNotification) -> None:
        if self._bot is None:
            return

        try:
            await self._bot.send_message(
                chat_id=notification.telegram_id,
                text=self._format_message(notification),
                disable_web_page_preview=True,
            )
        except TelegramAPIError as exc:
            await self._mark_notification_failed(notification_id, str(exc))
            logger.bind(
                telegram_id=notification.telegram_id,
                reminder_id=str(notification.reminder_id),
                notification_id=notification_id,
            ).warning(f"Telegram reminder notification failed: {exc}")
            return

        await self._mark_notification_sent(notification_id)
        logger.bind(
            telegram_id=notification.telegram_id,
            reminder_id=str(notification.reminder_id),
            notification_id=notification_id,
        ).info("Telegram reminder notification sent")

    @staticmethod
    def _get_token() -> str | None:
        if settings.telegram_bot_token is None:
            return None
        token = settings.telegram_bot_token.get_secret_value().strip()
        return token or None

    @staticmethod
    def _get_timezone() -> ZoneInfo:
        try:
            return ZoneInfo(settings.telegram_reminder_timezone)
        except ZoneInfoNotFoundError:
            logger.warning(
                f"Unknown TELEGRAM_REMINDER_TIMEZONE={settings.telegram_reminder_timezone}; using UTC"
            )
            return ZoneInfo("UTC")

    async def _fetch_active_reminders(self) -> list[asyncpg.Record]:
        query = """
            SELECT
                r.id AS reminder_id,
                r.contact_id,
                r.title,
                r.description,
                r.reminder_date,
                r.reminder_time,
                r.repeat_rule,
                r.early_reminder_minutes,
                r.early_reminder_repeat,
                c.display_name AS contact_name,
                c.owner_user_id AS user_id,
                owner.telegram_id
            FROM reminders r
            JOIN contacts c ON c.id = r.contact_id
            JOIN users owner ON owner.id = c.owner_user_id
            LEFT JOIN user_settings us ON us.user_id = owner.id
            WHERE r.completed = false
                AND c.is_archived = false
                AND owner.telegram_id IS NOT NULL
                AND COALESCE(us.notifications_enabled, true) = true
            ORDER BY r.reminder_date ASC, r.reminder_time ASC NULLS LAST
        """
        async with db_connection() as conn:
            return await conn.fetch(query)

    def _build_notifications(
        self,
        row: asyncpg.Record,
        now: datetime,
        window_start: datetime,
        timezone: ZoneInfo,
    ) -> list[ReminderNotification]:
        notifications: list[ReminderNotification] = []
        for occurrence_at in self._iter_occurrences(row, now, window_start, timezone):
            if window_start <= occurrence_at <= now:
                notifications.append(
                    self._make_notification(
                        row=row,
                        notification_type="main",
                        notification_key=f"main:{occurrence_at.isoformat()}",
                        occurrence_at=occurrence_at,
                        scheduled_at=occurrence_at,
                    )
                )

            early_minutes = row["early_reminder_minutes"]
            if early_minutes is None or early_minutes <= 0:
                continue

            early_at = occurrence_at - timedelta(minutes=early_minutes)
            if row["early_reminder_repeat"] == "daily":
                scheduled_at = early_at
                while scheduled_at < occurrence_at:
                    if window_start <= scheduled_at <= now:
                        notifications.append(
                            self._make_notification(
                                row=row,
                                notification_type="early",
                                notification_key=(
                                    f"early_daily:{occurrence_at.isoformat()}:{scheduled_at.date().isoformat()}"
                                ),
                                occurrence_at=occurrence_at,
                                scheduled_at=scheduled_at,
                            )
                        )
                    scheduled_at += timedelta(days=1)
            elif window_start <= early_at <= now:
                notifications.append(
                    self._make_notification(
                        row=row,
                        notification_type="early",
                        notification_key=f"early_once:{occurrence_at.isoformat()}",
                        occurrence_at=occurrence_at,
                        scheduled_at=early_at,
                    )
                )

        return notifications

    def _iter_occurrences(
        self,
        row: asyncpg.Record,
        now: datetime,
        window_start: datetime,
        timezone: ZoneInfo,
    ) -> list[datetime]:
        base_at = self._combine(row["reminder_date"], row["reminder_time"], timezone)
        early_minutes = row["early_reminder_minutes"] or 0
        max_until = now + timedelta(minutes=early_minutes, days=1)
        repeat_rule = row["repeat_rule"]

        if repeat_rule is None:
            return [base_at] if base_at <= max_until else []

        if repeat_rule == "daily":
            start_days = max(0, (window_start.date() - base_at.date()).days - 2)
            occurrence_at = base_at + timedelta(days=start_days)
            return self._collect_interval_occurrences(occurrence_at, max_until, timedelta(days=1))

        if repeat_rule == "weekly":
            start_weeks = max(0, ((window_start.date() - base_at.date()).days // 7) - 2)
            occurrence_at = base_at + timedelta(weeks=start_weeks)
            return self._collect_interval_occurrences(occurrence_at, max_until, timedelta(weeks=1))

        occurrences: list[datetime] = []
        occurrence_at = base_at
        while occurrence_at <= max_until:
            if occurrence_at >= window_start - timedelta(minutes=early_minutes, days=1):
                occurrences.append(occurrence_at)
            occurrence_at = (
                self._add_months(occurrence_at, 1)
                if repeat_rule == "monthly"
                else self._add_years(occurrence_at, 1)
            )
        return occurrences

    @staticmethod
    def _collect_interval_occurrences(
        first_occurrence_at: datetime,
        max_until: datetime,
        step: timedelta,
    ) -> list[datetime]:
        occurrences: list[datetime] = []
        occurrence_at = first_occurrence_at
        while occurrence_at <= max_until:
            occurrences.append(occurrence_at)
            occurrence_at += step
        return occurrences

    @staticmethod
    def _add_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    @staticmethod
    def _add_years(value: datetime, years: int) -> datetime:
        year = value.year + years
        day = min(value.day, calendar.monthrange(year, value.month)[1])
        return value.replace(year=year, day=day)

    @staticmethod
    def _combine(reminder_date: date, reminder_time: time | None, timezone: ZoneInfo) -> datetime:
        return datetime.combine(
            reminder_date,
            reminder_time or settings.telegram_reminder_default_time,
            tzinfo=timezone,
        )

    @staticmethod
    def _make_notification(
        row: asyncpg.Record,
        notification_type: str,
        notification_key: str,
        occurrence_at: datetime,
        scheduled_at: datetime,
    ) -> ReminderNotification:
        return ReminderNotification(
            reminder_id=row["reminder_id"],
            user_id=row["user_id"],
            contact_id=row["contact_id"],
            telegram_id=row["telegram_id"],
            contact_name=row["contact_name"],
            title=row["title"],
            description=row["description"],
            notification_type=notification_type,
            notification_key=notification_key,
            occurrence_at=occurrence_at,
            scheduled_at=scheduled_at,
        )

    async def _claim_notification(self, notification: ReminderNotification) -> int | None:
        query = """
            INSERT INTO reminder_notifications (
                reminder_id, user_id, contact_id, notification_type, notification_key,
                occurrence_at, scheduled_at, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'processing')
            ON CONFLICT (reminder_id, notification_key) DO NOTHING
            RETURNING id
        """
        async with db_transaction() as conn:
            return await conn.fetchval(
                query,
                notification.reminder_id,
                notification.user_id,
                notification.contact_id,
                notification.notification_type,
                notification.notification_key,
                notification.occurrence_at,
                notification.scheduled_at,
            )

    async def _mark_notification_sent(self, notification_id: int) -> None:
        query = """
            UPDATE reminder_notifications
            SET status = 'sent',
                sent_at = now(),
                error_message = NULL,
                updated_at = now()
            WHERE id = $1
        """
        async with db_transaction() as conn:
            await conn.execute(query, notification_id)

    async def _mark_notification_failed(self, notification_id: int, error_message: str) -> None:
        query = """
            UPDATE reminder_notifications
            SET status = 'failed',
                error_message = $2,
                updated_at = now()
            WHERE id = $1
        """
        async with db_transaction() as conn:
            await conn.execute(query, notification_id, error_message[:1000])

    @staticmethod
    def _format_message(notification: ReminderNotification) -> str:
        title = html.escape(notification.title)
        contact_name = html.escape(notification.contact_name)
        description = html.escape(notification.description or "").strip()
        occurrence_text = notification.occurrence_at.strftime("%d.%m.%Y в %H:%M")

        header = "Скоро событие" if notification.notification_type == "early" else "Напоминание"
        parts = [
            f"<b>{header} BirthSync</b>",
            f"<b>{title}</b>",
            f"Контакт: {contact_name}",
            f"Когда: {occurrence_text}",
        ]
        if description:
            parts.append(f"Описание: {description}")
        return "\n".join(parts)


telegram_bot_service = TelegramBotService()
