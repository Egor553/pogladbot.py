import asyncio
import platform
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from datetime import datetime, timedelta
import logging

# Настройка цикла событий для Windows
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
TOKEN = '8431173012:AAHAXemmpqtsSygY08xYKg__8pkh2ka3ZnQ'

# Определение состояний FSM
class OrderStates(StatesGroup):
    selecting_tariff_type = State()
    selecting_tariff = State()
    entering_address = State()
    entering_time = State()
    entering_date = State()
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
    
    welcome_text = """Привет! Я ПогладьБот — экономлю ваше время и силы на глажке одежды. Заказать можно снизу 👇

Что умеет бот:
* Экономит до 5 часов в неделю на глажке 💘
* Курьер бесплатно забирает и доставляет вещи 🚚
* Гладим аккуратно, с гарантией качества (повтор бесплатно или возврат)
* Абонементы и акции для постоянных клиентов 🎁
* Интеграция с AmoCRM для трекинга заказов 📊
* 24 часа на обработку — быстро и надежно ⏱️"""
    
    # Вставка видео (замени 'YOUR_VIDEO_FILE_ID' на file_id видео после загрузки и редактирования)
    # Чтобы убрать водяной знак и добавить "Погладь": используй CapCut (импорт видео → текст "Погладь" центр → удалить объект для знака → экспорт). Получи file_id, отправив видео боту.
    await message.answer_video(video='YOUR_VIDEO_FILE_ID', caption=welcome_text)
    
    await message.answer(welcome_text, reply_markup=get_start_menu())

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
            await callback.message.answer("Введите новое время (чч:мм):")
        elif data == "change_date":
            await state.set_state(OrderStates.entering_date)
            await callback.message.answer("Введите новую дату (дд.мм.гг):")
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
    await message.answer("Укажите удобное время (чч:мм):")
    await state.set_state(OrderStates.entering_time)

# Время
@dp.message(OrderStates.entering_time)
async def handle_time(message: types.Message, state: FSMContext):
    try:
        time_str = message.text.strip().replace(' ', '')  # Удаляем лишние пробелы
        dt_time = datetime.strptime(time_str, "%H:%M")
        await state.update_data(time=dt_time.strftime("%H:%M"))  # Нормализуем
        await message.answer("Укажите дату (дд.мм.гг):")
        await state.set_state(OrderStates.entering_date)
    except ValueError:
        await message.answer("Неверный формат времени. Используйте чч:мм (например, 18:00). Попробуйте снова.")

# Дата
@dp.message(OrderStates.entering_date)
async def handle_date(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip().replace(' ', '')
        dt_date = datetime.strptime(date_str, "%d.%m.%y")
        await state.update_data(date=dt_date.strftime("%d.%m.%y"))  # Нормализуем
        await message.answer("Введите ваш номер телефона:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderStates.entering_phone)
    except ValueError:
        await message.answer("Неверный формат даты. Используйте дд.мм.гг (например, 02.10.25). Попробуйте снова.")

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
    date = data.get('date', 'Не указано')
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
* Дата: {date}
* Номер телефона: {phone}
* Предварительная цена: {int(price)} ₽"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton(text="Изменить адрес", callback_data="change_address")],
        [InlineKeyboardButton(text="Изменить время", callback_data="change_time")],
        [InlineKeyboardButton(text="Изменить дату", callback_data="change_date")],
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
1. Убрать стартовую картинку (что умеет бот на главный экран вставить видео, которое я тебе скинул, убери водяной знак и добавить надпись погладь).
2. На главной экран вставь видео, которое я тебе скинул (убери водяной знак и добавь надпись 'Погладь').
3. Исправить косяк со временем.
4. Где этапы добавить картину успешных работ отзывы, выдавая по 3 офера в конце призыв к действию сделать заказ.
5. Пока можешь направить вопрос основателю проекта кнопка написать."""
    
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
    
    # Офер 1 (группа 1-5 с фото)
    reviews_group1 = """Офер 1: Отзывы 1-5
1. Марина, 34 — ★★★★★ Сервис выручает каждую неделю. Всё чётко. Крайне рекомендую.
2. Андрей, 29 — ★★★★★ Рубашки идеальные, приехали. Мне нравится.
3. Лидия, 56 — ★★★★★ Очень удобно для меня, спасибо.
4. Оксана, 41 — ★★★★★ Глажка — не мой конёк, теперь всё за меня делают, спасибо!!!
5. Павел, 37 — ★★★★★ Приятно удивлён качеством и скоростью."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEBWjdZ2AFss5xKwQJan-OuPo8cZS0AALd_jEbkOvpSpFD-iw9jQuHAQADAgADeQADNgQ', caption=reviews_group1)
    
    # Офер 2 (группа 6-9 с фото)
    reviews_group2 = """Офер 2: Отзывы 6-9
6. ★★★★★ Быстро и идеально!
7. ★★★★★ Лучший сервис!
8. ★★★★★ Вещи — огонь!
9. ★★★★★ Идеально"""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEB2jdZ3cnQwAB1nqVx_3qOiNdK0bGygAC4f4xG5Dr6UogN6n-4DG-ggEAAwIAA3kAAzYE', caption=reviews_group2)
    
    # Офер 3 (группа 10-14 с фото)
    reviews_group3 = """Офер 3: Отзывы 10-14
10. Светлана, 67 лет — ★★★★★ Здоровье уже не то, тяжёлый утюг держать сложно. А выглядеть опрятно хочется. Очень благодарна сервису - курьер забирает и возвращает вещи, всё отглажено с душой. Для меня это больше, чем просто услуга.
11. Максим, отец семейства - ★★★★★ Мы с женой постоянно спорили: кому гладить горы школьной формы и наши рубашки. С ПогладьБот этот вопрос отпал. Никаких конфликтов, вещи приходят чистые, сложенные, дети довольны, и мы тоже.
12. Кира, студентка — ★★★★★ Сессия, подработки и готовка — и времени на глажку не было совсем. Я привыкла носить мятые вещи, честно. Попробовала сервис ради интереса и теперь заказываю регулярно. Это такой кайф — просто носить всё чистое и аккуратное, а не тратить ночь перед экзаменом на утюг.
13. Игорь, айтишник — ★★★★★ Работаю из дома, но постоянно участвую в онлайн-встречах. В мятой футболке ещё сойдёт, а вот рубашки — позор. Жена устала мне напоминать, я сам всё откладывал. Теперь раз в неделю отдаю вещи, и вопрос закрыт. Выгляжу как человек, а времени на это не трачу.
14. Полина, маркетолог — ★★★★★ У нас с мужем маленький ребёнок, и я думала, что глажка — это неизбежно и бесконечно. Но сервис показал, что можно жить по-другому. Теперь я провожу вечер с ребёнком, а не с гладильной доской. Это реально про качество жизни."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIECWjdZ4ci5UEa6lInky19EpffuZORAALj_jEbkOvpSilMEP3byErwAQADAgADeQADNgQ', caption=reviews_group3)
    
    # Призыв к действию
    call_to_action = "Не откладывайте — сделайте заказ сейчас и сэкономьте время!"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать заказ", callback_data="make_order")],
    ])
    await message.answer(call_to_action, reply_markup=keyboard)

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
    text = "Пока можешь направить вопрос основателю проекта"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать основателю", url="https://t.me/OlegMahalov")],
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
