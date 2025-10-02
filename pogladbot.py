import asyncio
import platform
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

# Настройка цикла событий для Windows
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
TOKEN = '8431173012:AAGLU7aN9DlIfIHt7E7ZAgjMg7ZUDp6rY0c'

# Определение состояний FSM
class OrderStates(StatesGroup):
    selecting_tariff_type = State()
    selecting_tariff = State()
    entering_address = State()
    entering_time = State()
    entering_phone = State()
    confirming_order = State()
    selecting_payment_method = State()
    leaving_review = State()

# Инициализация бота и диспетчера
try:
    bot = Bot(token=TOKEN)
except Exception as e:
    logging.error(f"Ошибка инициализации бота: {e}")
    raise SystemExit("Проверьте токен бота и убедитесь, что он действителен.")

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# База данных в памяти
orders = {}
reviews = []
users = {}

# Стартовое меню
def get_start_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать заказ", callback_data="make_order")],
        [InlineKeyboardButton(text="Этапы работы", callback_data="work_stages")],
        [InlineKeyboardButton(text="Успешные примеры и отзывы", callback_data="examples_reviews")],
        [InlineKeyboardButton(text="О нас", callback_data="about_us")],
        [InlineKeyboardButton(text="Вопросы к нам (техподдержка)", callback_data="support")],
    ])
    return keyboard

# /start
@dp.message(Command('start', 'Старт', 'start'))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    users[user_id] = {'last_activity': datetime.now(), 'promo': None, 'first_order': True}
    
    welcome_text = "Привет! Я ПогладьБот — экономлю ваше время и силы на глажке одежды. Заказать можно снизу 👇"
    await message.answer_photo(photo='AgACAgIAAxkBAAIEA2jdZwx79gl9ltjC8vkuJ73wyYCtAALc_jEbkOvpSkLFxuDzEW-uAQADAgADeQADNgQ', caption=welcome_text)
    value_text = "С нашим сервисом вы экономите до 5 часов в неделю и занимаетесь самым важным 💘. Больше не нужно ехать в прачечную, переплачивать или гладить самим — всё сделаем мы.\nНа первый заказ есть сюрприз 🤫🎁 Чтобы узнать что мы тебе подарили, жми 'Сделать заказ'"
    await message.answer(value_text, reply_markup=get_start_menu())

# Callback handler
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    try:
        if data == "make_order":
            await handle_make_order(callback.message, state)
        elif data == "work_stages":
            await handle_work_stages(callback.message)
        elif data == "examples_reviews":
            await handle_examples_reviews(callback.message)
        elif data == "about_us":
            await handle_about_us(callback.message)
        elif data == "support":
            await handle_support(callback.message)
        elif data.startswith("tariff_type_"):
            await handle_tariff_type(callback, state)
        elif data.startswith("tariff_"):
            await handle_select_tariff(callback, state)
        elif data == "change_address":
            await state.set_state(OrderStates.entering_address)
            await callback.message.answer("Введите новый адрес:")
        elif data == "change_time":
            await state.set_state(OrderStates.entering_time)
            await callback.message.answer("Укажите удобное время: Например: 02.10.25 18:00")
        elif data == "change_phone":
            await state.set_state(OrderStates.entering_phone)
            await callback.message.answer("Введите ваш номер телефона:")
        elif data == "back_to_tariffs":
            await handle_make_order(callback.message, state)
        elif data == "confirm_order":
            await show_payment_methods(callback.message, state)
        elif data.startswith("payment_"):
            await handle_payment_method(callback, state)
        elif data == "leave_review":
            await state.set_state(OrderStates.leaving_review)
            await callback.message.answer("Оставьте отзыв: укажите звезды (1-5), комментарий и разрешение на публикацию (да/нет). Формат: 5\nОтличный сервис!\nда")
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка в обработке callback: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте снова или обратитесь в поддержку.")

# Сделать заказ
async def handle_make_order(message: types.Message, state: FSMContext):
    text = "У нас есть сюрприз для вас 🎁\nНа первый заказ действует акция — каждая третья вещь бесплатно:\nПлатите за 2, гладим 3\nПлатите за 4, гладим 6\nПлатите за 10, гладим 15"
    await message.answer(text)
    
    text_tariffs = """Наши тарифы:
* Любая одежда - 250 рублей
* 10 любых вещей - 2000 рублей
* 10 любых вещей со стиркой - 3000 рублей
Курьер — бесплатно. Срок: привозим вещи на следующий день."""
    await message.answer(text_tariffs)
    
    await message.answer("Выберите количество вещей:")
    await state.set_state(OrderStates.selecting_tariff)

# Выбор количества вещей
@dp.message(OrderStates.selecting_tariff)
async def handle_select_items(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        await state.update_data(quantity=quantity)
        await message.answer("Введите адрес в свободной форме: Например: Ленина, 76")
        await state.set_state(OrderStates.entering_address)
    except ValueError:
        await message.answer("Введите число вещей, например: 5")

# Адрес
@dp.message(OrderStates.entering_address)
async def handle_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Укажите удобное время: Например: 02.10.25 18:00")
    await state.set_state(OrderStates.entering_time)

# Время
@dp.message(OrderStates.entering_time)
async def handle_time(message: types.Message, state: FSMContext):
    chlyabinsk_tz = ZoneInfo("Asia/Yekaterinburg")  # Челябинск, UTC+5
    now_local = datetime.now(chlyabinsk_tz)  # Инициализация вне try
    
    try:
        # Попытка парсинга времени в формате "дд.мм.гг чч:мм"
        time_str = message.text.strip()
        dt = datetime.strptime(time_str, "%d.%m.%y %H:%M")
        dt_local = dt.replace(tzinfo=chlyabinsk_tz)
        
        # Проверка, не находится ли время в прошлом
        if dt_local < now_local:
            raise ValueError("Указанное время находится в прошлом. Пожалуйста, выберите будущее время.")
        
        await state.update_data(time=time_str)
        await message.answer("Введите ваш номер телефона:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderStates.entering_phone)
    except ValueError as e:
        error_msg = str(e) if str(e) else "Неверный формат времени. Используйте формат: дд.мм.гг чч:мм (например, 02.10.25 18:00). Убедитесь, что между датой и временем есть пробел."
        # Создание клавиатуры с быстрыми кнопками
        quick_times = [
            [KeyboardButton(text=f"{now_local.strftime('%d.%m.%y %H:%M')} (сейчас)")],
            [KeyboardButton(text=f"{(now_local + timedelta(hours=1)).strftime('%d.%m.%y %H:%M')} (+1 час)")],
            [KeyboardButton(text=f"{(now_local + timedelta(hours=2)).strftime('%d.%m.%y %H:%M')} (+2 часа)")],
            [KeyboardButton(text=f"{(now_local + timedelta(hours=3)).strftime('%d.%m.%y %H:%M')} (+3 часа)")],
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=quick_times, resize_keyboard=True, one_time_keyboard=True)
        await message.answer(error_msg + " Попробуйте снова или выберите время ниже:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при обработке времени: {e}")
        await message.answer("Произошла ошибка при обработке времени. Пожалуйста, попробуйте снова в формате дд.мм.гг чч:мм (например, 02.10.25 18:00).")

# Номер телефона
@dp.message(OrderStates.entering_phone)
async def handle_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await show_confirmation(message, state)

# Подтверждение
async def show_confirmation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tariff = f"{data.get('quantity', 0)} вещей по тарифу (см. выше)"
    address = data.get('address', 'Не указан')
    time = data.get('time', 'Не указано')
    phone = data.get('phone', 'Не указан')
    quantity = data.get('quantity', 0)
    first_order = users.get(message.from_user.id, {}).get('first_order', True)
    
    base_price = 250 * quantity if quantity <= 10 else (2000 if quantity == 10 else 3000)
    if first_order:
        price = base_price * 2 / 3  # 2/3 от стоимости для первого заказа
    else:
        price = base_price  # Полная стоимость для остальных
    
    text = f"""Итог:
* Тариф: {tariff}
* Адрес: {address}
* Время: {time}
* Номер телефона: {phone}
* Предварительная цена: {int(price)} ₽"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton(text="Изменить адрес", callback_data="change_address")],
        [InlineKeyboardButton(text="Изменить время", callback_data="change_time")],
        [InlineKeyboardButton(text="Изменить номер", callback_data="change_phone")],
        [InlineKeyboardButton(text="Назад к тарифам", callback_data="back_to_tariffs")],
    ])
    
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(OrderStates.confirming_order)

# Выбор способа оплаты
async def show_payment_methods(message: types.Message, state: FSMContext):
    text = "Отлично! Заказ принят ✅ Оплата производится курьеру картой или наличными"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить картой курьеру", callback_data="payment_card")],
        [InlineKeyboardButton(text="Оплатить наличными курьеру", callback_data="payment_cash")],
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(OrderStates.selecting_payment_method)

# Обработка способа оплаты
async def handle_payment_method(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    payment = callback.data.split("_")[1]
    orders[user_id] = data.copy()
    orders[user_id]['status'] = 'Принят'
    orders[user_id]['payment'] = payment
    
    if payment == "card":
        await callback.message.answer("Заказ принят! Номер заявки: 12345. Оплатите картой курьеру при доставке.")
    elif payment == "cash":
        await callback.message.answer("Заказ принят! Номер заявки: 12345. Оплатите наличными курьеру при доставке.")
    
    users[user_id]['first_order'] = False  # Отмечаем, что это не первый заказ
    await state.clear()

# Этапы работы
async def handle_work_stages(message: types.Message):
    text = """Процесс сотрудничества 🤝
* Вы делаете заказ — прямо в боте.
* Курьер бесплатно приезжает — забирает вещи, которые вы заранее собрали в пакет в удобное время.
* Мы гладим профессионально — аккуратно, бережно, быстро.
* Курьер доставляет обратно — чистые и выглаженные вещи возвращаются к вам. Таким образом, единственная Ваша задача — оформить заказ в боте и собрать вещи в пакет 😊"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В главное меню", callback_data="start")],
        [InlineKeyboardButton(text="Оформить заказ", callback_data="make_order")],
    ])
    
    await message.answer(text, reply_markup=keyboard)

# Успешные примеры и отзывы
async def handle_examples_reviews(message: types.Message):
    # Самый козырный отзыв с фотографией
    top_review = "Анастасия, мама двоих — ★★★★★ С двумя детьми и работой времени на глажку не оставалось совсем. Одежда копилась неделями, я уже смирилась, что будем ходить помятыми. Заказала ПогладьБот — и на следующий день всё вернули аккуратное, сложенное, будто новое. Чувствую себя человеком, а не вечной прачкой."
    await message.answer_photo(photo='AgACAgIAAxkBAAIEDWjdZ7xFZQfMjyEXmqD2UIKlWzO5AALq_jEbkOvpSqrckIaGN9YvAQADAgADeQADNgQ', caption=top_review)
    
    # Остальные отзывы с распределенными фотографиями
    reviews_group1 = """Отзывы 1-5:
1. Марина, 34 — ★★★★★ Сервис выручает каждую неделю. Всё чётко. Крайне рекомендую.
2. Андрей, 29 — ★★★★★ Рубашки идеальные, приехали. Мне нравится.
3. Лидия, 56 — ★★★★★ Очень удобно для меня, спасибо.
4. Оксана, 41 — ★★★★★ Глажка — не мой конёк, теперь всё за меня делают, спасибо!!!
5. Павел, 37 — ★★★★★ Приятно удивлён качеством и скоростью."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEBWjdZ2AFss5xKwQJan-OuPo8cZS0AALd_jEbkOvpSpFD-iw9jQuHAQADAgADeQADNgQ', caption=reviews_group1)
    
    reviews_group2 = """Отзывы 6-9:
6. ★★★★★ Быстро и идеально!
7. ★★★★★ Лучший сервис!
8. ★★★★★ Вещи — огонь!
9. ★★★★★ Идеально"""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEB2jdZ3cnQwAB1nqVx_3qOiNdK0bGygAC4f4xG5Dr6UogN6n-4DG-ggEAAwIAA3kAAzYE', caption=reviews_group2)
    
    reviews_group3 = """Отзывы 10-14:
10. Светлана, 67 лет — ★★★★★ Здоровье уже не то, тяжёлый утюг держать сложно. А выглядеть опрятно хочется. Очень благодарна сервису - курьер забирает и возвращает вещи, всё отглажено с душой. Для меня это больше, чем просто услуга.
11. Максим, отец семейства - ★★★★★ Мы с женой постоянно спорили: кому гладить горы школьной формы и наши рубашки. С ПогладьБот этот вопрос отпал. Никаких конфликтов, вещи приходят чистые, сложенные, дети довольны, и мы тоже.
12. Кира, студентка — ★★★★★ Сессия, подработки и готовка — и времени на глажку не было совсем. Я привыкла носить мятые вещи, честно. Попробовала сервис ради интереса и теперь заказываю регулярно. Это такой кайф — просто носить всё чистое и аккуратное, а не тратить ночь перед экзаменом на утюг.
13. Игорь, айтишник — ★★★★★ Работаю из дома, но постоянно участвую в онлайн-встречах. В мятой футболке ещё сойдёт, а вот рубашки — позор. Жена устала мне напоминать, я сам всё откладывал. Теперь раз в неделю отдаю вещи, и вопрос закрыт. Выгляжу как человек, а времени на это не трачу.
14. Полина, маркетолог — ★★★★★ У нас с мужем маленький ребёнок, и я думала, что глажка — это неизбежно и бесконечно. Но сервис показал, что можно жить по-другому. Теперь я провожу вечер с ребёнком, а не с гладильной доской. Это реально про качество жизни."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIECWjdZ4ci5UEa6lInky19EpffuZORAALj_jEbkOvpSilMEP3byErwAQADAgADeQADNgQ', caption=reviews_group3)
    
    reviews_group4 = """Отзывы 15-18:
15. ★★★★★ Не ожидал такого сервиса в нашем городе. Очень удобно!
16. ★★★★★ Курьер всегда вежливый, вещи в пакетах, всё чисто и аккуратно.
17. ★★★★★ Экономия нервов и времени. Пять звёзд!
18. ★★★★★ Сначала сомневалась, а теперь заказываю каждую неделю."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEC2jdZ6sAAfgCFZS2watT0AbLtGGTqAAC6P4xG5Dr6UoQSp_vf5o0mAEAAwIAA3kAAzYE', caption=reviews_group4)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Хочу так же", callback_data="make_order")],
        [InlineKeyboardButton(text="Задать вопрос", callback_data="support")],
        [InlineKeyboardButton(text="Оставить отзыв", callback_data="leave_review")],
    ])
    await message.answer("Действия:", reply_markup=keyboard)

# О нас
async def handle_about_us(message: types.Message):
    text = """ПогладьБот — сервис с 2024 года. По Челябинску уже сэкономили время 900+ клиентам. Средний срок — 24 часа. Команда: 10+ курьеров и 10+ сотрудников по глажке.
Факты:
* Контроль качества в 3 этапа: осмотр, глажка, финальная проверка.
* Упаковка: аккуратная укладка чтобы доехало без заломов, пакет защищает от влаги.
* Честные сроки: обычно на следующий день, в течение дня — по согласованию.
* Гарантия: если результат не устроил — повторная обработка бесплатно или возврат средств.
* Удобство: курьер бесплатно, можно сдавать вещи хоть каждый день.
* Поддержка: живой оператор отвечает в рабочие часы, в остальное время — бот-помощник."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIED2jdZ-20723XKulmd-KCeY9ebsV3AALr_jEbkOvpSg1Zsk6-nJcNAQADAgADeQADNgQ', caption=text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать заказ", callback_data="make_order")],
        [InlineKeyboardButton(text="Задать вопрос", callback_data="support")],
    ])
    
    await message.answer(text, reply_markup=keyboard)

# Техподдержка
async def handle_support(message: types.Message):
    text = "Напиши твой вопрос нам, мы ответим (пока можешь направить на личку Олегу)"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать Олегу", url="https://t.me/OlegMahalov")],
    ])
    await message.answer(text, reply_markup=keyboard)

# Хэндлер для обработки фотографий
@dp.message()
async def handle_photo(message: types.Message):
    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        await message.answer(f"Получен file_id: {file_id}")

# Автосообщения
async def check_inactive_users():
    while True:
        now = datetime.now()
        for user_id, info in list(users.items()):
            delta = (now - info['last_activity']).total_seconds() / 60
            if delta > 3 and 'sent_3min' not in info:
                await bot.send_message(user_id, "На первый заказ действует акция — каждая третья вещь бесплатно 😄\nПодробнее — в боте.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сделать заказ", callback_data="make_order")]]))
                info['sent_3min'] = True
        await asyncio.sleep(60)

# Запуск
async def main():
    try:
        # Запуск фонового задания для проверки неактивных пользователей
        inactive_task = asyncio.create_task(check_inactive_users())
        
        # Запуск цикла опроса
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        # Остановка бота при прерывании
        logging.info("Получен запрос на остановку бота. Выполняется graceful shutdown...")
        await asyncio.sleep(5)  # Задержка для избежания flood control
        await bot.close()
        if not inactive_task.done():
            inactive_task.cancel()
            try:
                await inactive_task
            except asyncio.CancelledError:
                logging.info("Фоновое задание check_inactive_users успешно остановлено.")
    except Exception as e:
        logging.error(f"Ошибка при запуске поллинга: {e}")
        raise SystemExit("Не удалось запустить бота. Проверьте токен и соединение.")
    finally:
        await asyncio.sleep(5)  # Дополнительная задержка перед окончательным закрытием
        await bot.close()
        logging.info("Бот остановлен.")

if __name__ == '__main__':
    asyncio.run(main())
