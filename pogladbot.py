import asyncio
import platform
import json
import aiohttp
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

# Класс для работы с amoCRM API
class AmoCRMClient:
    def __init__(self):
        self.tokens_file = "amocrm_tokens.json"
        # Значения по умолчанию, чтобы код работал без внешнего JSON
        self.default_tokens = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImIzNTQ1MDkxNGZkYTkzMTA3NThmZDNjNzU5NTE3YTMzNjJhM2FjOTkxYTc4NjE3ODAyNmM1ZDk3YjUzM2I0MGUzN2Y0MGQyNWJiMTc4OTg0In0.eyJhdWQiOiI4YzdjNzhkOS05YWI1LTQ4NjAtYTIyNi1jODY4OGYyNTVhMzgiLCJqdGkiOiJiMzU0NTA5MTRmZGE5MzEwNzU4ZmQzYzc1OTUxN2EzMzYyYTNhYzk5MWE3ODYxNzgwMjZjNWQ5N2I1MzNiNDBlMzdmNDBkMjViYjE3ODk4NCIsImlhdCI6MTc2MDYzNDkzNSwibmJmIjoxNzYwNjM0OTM1LCJleHAiOjE4NDA1NzkyMDAsInN1YiI6IjEyOTE0Njg2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyNjMyMDMwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsIm5vdGlmaWNhdGlvbnMiXSwidXNlcl9mbGFncyI6MCwiaGFzaF91dWlkIjoiOWMxYTA5MDctOGFmYS00YTgyLTg0NzUtYzhlMjE1MjNiNjE2IiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.RgBvamYffXi2rAQAR9mxuuRMhISfGsVNKLYekgI8ochnSKtBVUySwbwWUH5OLNNMNmuk9WmJaHYCoy5koN_WzWZTrsC-CkgJrD6VkocwyLj8D-kaO-r_bk8uOlS7GSVVsPrUumfWgXF_4SmNxnWRqe7ZwqPQz9W4OxL0z_K6aRvaXtSGIRZ6lLMt6RX156rmij-Lkk0YNbytr92kgWLWRbGpg6l9e50YaZAlEczOfWIqbu4mdMPiMeYuxfncPNt2t_six8HnjkaiHGfsOwXkaJXNW4-EEikhdWIRHMjBUzbBsAdnUc2Xz9vmMpC73sIGpVEOljNoNzLeO6mEmsZxew",
            "integration_id": "8c7c78d9-9ab5-4860-a226-c8688f255a38",
            "secret_key": "pxNPleWUHwWljqdRIPsa8xa77LKseLeIaIcjKW6U7HZn9k8M38cFbeAJON92A9rU",
            "pipeline_id": "10143858",
            "api_domain": "api-b.amocrm.ru",
            "base_domain": "amocrm.ru",
            "account_id": 32632030,
            "subdomain": None,
            "first_stage_id": None,
            "last_check_timestamp": None,
        }
        self.tokens = self.load_tokens()
        self.session = None
        
    def validate_tokens(self):
        required_fields = [
            "access_token",
            "api_domain",
            "pipeline_id",
        ]
        missing = [key for key in required_fields if not self.tokens.get(key)]
        if missing:
            logging.error(f"Отсутствуют обязательные поля в токенах amoCRM: {', '.join(missing)}")
            raise SystemExit("Некорректная конфигурация amoCRM. Заполните access_token, api_domain и pipeline_id.")

    def load_tokens(self):
        try:
            with open(self.tokens_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"Файл токенов {self.tokens_file} не найден. Использую значения по умолчанию из кода.")
            return dict(self.default_tokens)
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка парсинга JSON в файле токенов: {e}. Использую значения по умолчанию из кода.")
            return dict(self.default_tokens)
    
    def save_tokens(self):
        try:
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                json.dump(self.tokens, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Ошибка сохранения токенов: {e}")
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.tokens.get("access_token", "")}',
            'Content-Type': 'application/json'
        }
    
    async def make_request(self, method, url, data=None, params=None, retries=3):
        session = await self.get_session()
        headers = self.get_headers()
        
        for attempt in range(retries):
            try:
                logging.info(f"AmoCRM API запрос: {method} {url}")
                if data:
                    logging.info(f"Тело запроса: {json.dumps(data, ensure_ascii=False)}")
                if params:
                    logging.info(f"Query params: {params}")
                
                async with session.request(method, url, headers=headers, params=params, json=data) as response:
                    response_text = await response.text()
                    logging.info(f"AmoCRM API ответ: {response.status} - {response_text}")
                    
                    if response.status == 200 or response.status == 201:
                        return await response.json()
                    elif response.status == 401:
                        logging.error("Ошибка авторизации amoCRM - проверьте токен")
                        return None
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        logging.warning(f"Rate limit amoCRM, ожидание {wait_time} секунд")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status >= 500:
                        wait_time = 5 * (attempt + 1)
                        logging.warning(f"Ошибка сервера amoCRM {response.status}, ожидание {wait_time} секунд")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logging.error(f"Ошибка amoCRM API: {response.status} - {response_text}")
                        return None
                        
            except Exception as e:
                logging.error(f"Ошибка запроса к amoCRM: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None
        
        return None
    
    async def get_account_info(self):
        url = f"https://{self.tokens['api_domain']}/api/v4/account"
        result = await self.make_request('GET', url)
        if result:
            account_data = result.get('account', {})
            self.tokens['subdomain'] = account_data.get('subdomain')
            self.tokens['account_id'] = account_data.get('id')
            self.save_tokens()
            logging.info(f"Получена информация об аккаунте: subdomain={self.tokens['subdomain']}, id={self.tokens['account_id']}")
        return result
    
    async def get_pipeline_stages(self, pipeline_id):
        url = f"https://{self.tokens['api_domain']}/api/v4/leads/pipelines/{pipeline_id}"
        result = await self.make_request('GET', url)
        if result:
            # /api/v4/leads/pipelines/{pipeline_id} возвращает объект пайплайна
            stages = result.get('_embedded', {}).get('stages', [])
            if stages:
                first_stage_id = stages[0]['id']
                self.tokens['first_stage_id'] = first_stage_id
                self.save_tokens()
                logging.info(f"Получены этапы воронки {pipeline_id}, первый этап: {first_stage_id}")
                return stages
        return None
    
    async def find_contact_by_phone(self, phone):
        url = f"https://{self.tokens['api_domain']}/api/v4/contacts"
        params = {'query': phone}
        result = await self.make_request('GET', url, params=params)
        if result:
            contacts = result.get('_embedded', {}).get('contacts', [])
            for contact in contacts:
                custom_fields = contact.get('custom_fields_values', [])
                for field in custom_fields:
                    if field.get('field_code') == 'PHONE':
                        values = field.get('values', [])
                        for value in values:
                            if value.get('value') == phone:
                                logging.info(f"Найден существующий контакт: {contact['id']}")
                                return contact['id']
        return None
    
    async def create_contact(self, name, phone, telegram_id):
        url = f"https://{self.tokens['api_domain']}/api/v4/contacts"
        data = {
            "name": name,
            "custom_fields_values": [
                {
                    "field_code": "PHONE",
                    "values": [{"value": phone}]
                }
            ],
            "note": f"Telegram ID: {telegram_id}"
        }
        result = await self.make_request('POST', url, data)
        if result:
            contact_id = result.get('_embedded', {}).get('contacts', [{}])[0]['id']
            logging.info(f"Создан новый контакт: {contact_id}")
            return contact_id
        return None
    
    async def create_lead(self, name, price, contact_id, address, time, date, quantity, payment_method):
        url = f"https://{self.tokens['api_domain']}/api/v4/leads"
        data = {
            "name": name,
            "price": price,
            "pipeline_id": int(self.tokens['pipeline_id']),
            "status_id": int(self.tokens['first_stage_id']),
            "_embedded": {
                "contacts": [{"id": contact_id}]
            },
            "custom_fields_values": [
                {
                    "field_name": "Адрес доставки",
                    "values": [{"value": address}]
                },
                {
                    "field_name": "Время",
                    "values": [{"value": time}]
                },
                {
                    "field_name": "Дата",
                    "values": [{"value": date}]
                },
                {
                    "field_name": "Количество вещей",
                    "values": [{"value": str(quantity)}]
                },
                {
                    "field_name": "Способ оплаты",
                    "values": [{"value": payment_method}]
                }
            ]
        }
        result = await self.make_request('POST', url, data)
        if result:
            lead_id = result.get('_embedded', {}).get('leads', [{}])[0]['id']
            logging.info(f"Создана новая сделка: {lead_id}")
            return lead_id
        return None
    
    async def get_lead_notes(self, lead_id, since_timestamp=None):
        url = f"https://{self.tokens['api_domain']}/api/v4/leads/{lead_id}/notes"
        params = {}
        if since_timestamp:
            params['filter[created_at][from]'] = since_timestamp
        
        result = await self.make_request('GET', url, params=params)
        if result:
            notes = result.get('_embedded', {}).get('notes', [])
            logging.info(f"Получено {len(notes)} примечаний для сделки {lead_id}")
            return notes
        return []

# Инициализация клиента amoCRM
amocrm_client = AmoCRMClient()

# Токен бота
TOKEN = '8431173012:AAGrrww8iKW1nNkdCc7b5QUKoaPZxaG-qDg'

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
    # Проверяем токен на корректность
    if not TOKEN or len(TOKEN) < 10 or ':' not in TOKEN:
        raise ValueError("Некорректный формат токена")
    
    # Дополнительная проверка формата токена
    parts = TOKEN.split(':')
    if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) < 20:
        raise ValueError("Некорректный формат токена")
    
    bot = Bot(token=TOKEN)
    logging.info(f"Токен бота: {TOKEN[:10]}...{TOKEN[-10:]}")
    logging.info("Попытка подключения к Telegram API...")
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
    
    # Отправка видео с подписью и клавиатурой
    await message.answer_video(
        video='BAACAgIAAxkBAAIFamjmseBYjm6p6XIhRzXJ_CoknhS4AAKwgwACNEo4S9T8BovJAUfONgQ',
        caption=welcome_text,
        reply_markup=get_start_menu()
    )

# Тестовая команда для проверки токена бота
@dp.message(Command('test_token'))
async def test_token_handler(message: types.Message):
    try:
        me = await bot.get_me()
        await message.answer(f"✅ Токен действителен!\nБот: @{me.username}\nИмя: {me.first_name}")
    except Exception as e:
        await message.answer(f"❌ Ошибка токена: {e}")

# Тестовая команда для проверки интеграции с amoCRM
@dp.message(Command('test_amocrm'))
async def test_amocrm_handler(message: types.Message):
    try:
        user_id = message.from_user.id
        if user_id not in users:
            users[user_id] = {'last_activity': datetime.now(), 'promo': None, 'first_order': True}

        test_data = {
            'phone': '+79990000000',
            'address': 'Тестовый адрес, 1',
            'time': '12:00',
            'date': datetime.now().strftime('%d.%m.%y'),
            'quantity': 3,
        }

        await message.answer('Создаю тестовую сделку в amoCRM...')
        await create_amocrm_order(user_id, test_data, 'card', message.from_user)

        lead_id = orders.get(user_id, {}).get('amocrm_lead_id')
        if lead_id:
            await message.answer(f'Готово. Создана тестовая сделка ID: {lead_id}. Проверьте в amoCRM воронку {amocrm_client.tokens.get("pipeline_id")}.')
        else:
            await message.answer('Не удалось создать тестовую сделку. Посмотрите логи сервера на предмет ошибок amoCRM.')
    except Exception as e:
        logging.error(f"Ошибка тестовой команды amoCRM: {e}")
        await message.answer('Произошла ошибка при создании тестовой сделки. Проверьте логи.')

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
    if message.text is None:
        await message.answer("Пожалуйста, введите число вещей текстом, например: 5")
        return
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
        time_str = message.text.strip().replace(' ', '')
        dt_time = datetime.strptime(time_str, "%H:%M")
        await state.update_data(time=dt_time.strftime("%H:%M"))
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
        await state.update_data(date=dt_date.strftime("%d.%m.%y"))
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
    
    # Интеграция с amoCRM
    try:
        await create_amocrm_order(user_id, data, payment, callback.from_user)
    except Exception as e:
        logging.error(f"Ошибка создания заказа в amoCRM: {e}")
        await callback.message.answer("⚠️ Заказ принят, но произошла ошибка при отправке в CRM. Обратитесь в поддержку.")
    
    if payment == "card":
        await callback.message.answer("Заказ принят! Номер заявки: 12345. Оплатите картой курьеру при доставке.")
    elif payment == "cash":
        await callback.message.answer("Заказ принят! Номер заявки: 12345. Оплатите наличными курьеру при доставке.")
    
    users[user_id]['first_order'] = False
    await state.clear()

# Функция создания заказа в amoCRM
async def create_amocrm_order(user_id, order_data, payment_method, user_info):
    try:
        # Получаем информацию о пользователе
        name = f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
        if not name:
            name = user_info.username or f"Пользователь {user_id}"
        
        phone = order_data.get('phone', '')
        address = order_data.get('address', '')
        time = order_data.get('time', '')
        date = order_data.get('date', '')
        quantity = order_data.get('quantity', 0)
        
        # Рассчитываем цену
        first_order = users.get(user_id, {}).get('first_order', True)
        base_price = 250 * quantity if quantity <= 10 else (2000 if quantity == 10 else 3000)
        price = int(base_price * 2 / 3) if first_order else base_price
        
        # Ищем существующий контакт по телефону
        contact_id = await amocrm_client.find_contact_by_phone(phone)
        
        # Если контакт не найден, создаем новый
        if not contact_id:
            contact_id = await amocrm_client.create_contact(name, phone, user_id)
            if not contact_id:
                logging.error(f"Не удалось создать контакт для пользователя {user_id}")
                return
        
        # Создаем сделку
        lead_name = f"Заказ #{quantity} вещей - {name}"
        payment_text = "картой курьеру" if payment_method == "card" else "наличными курьеру"
        
        lead_id = await amocrm_client.create_lead(
            lead_name, price, contact_id, address, time, date, quantity, payment_text
        )
        
        if lead_id:
            # Сохраняем ID сделки в локальной базе
            orders[user_id]['amocrm_lead_id'] = lead_id
            logging.info(f"Успешно создан заказ в amoCRM: сделка {lead_id}, контакт {contact_id}")
        else:
            logging.error(f"Не удалось создать сделку для пользователя {user_id}")
            
    except Exception as e:
        logging.error(f"Ошибка при создании заказа в amoCRM: {e}")
        raise

# Этапы работы
async def handle_work_stages(message: types.Message):
    text = """Процесс сотрудничества 🤝
1. Убрать стартовую картинку (что умеет бот на главный экран вставить видео, которое я тебе скинул, убери водяной знак и добавить надпись погладь).
2. На главной экран вставь видео, которое я тебе скинул (убери водяной знак и добавь надпись 'Погладь').
3. Исправить косяк со временем.
4. Где этапы добавить картину успешных работ отзывы, выдая по 3 офера в конце призыв к действию сделать заказ.
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
    
    # Офер 1 (3 отзыва с фото)
    offer1 = """Офер 1:
1. Марина, 34 — ★★★★★ Сервис выручает каждую неделю. Всё чётко. Крайне рекомендую.
2. Андрей, 29 — ★★★★★ Рубашки идеальные, приехали. Мне нравится.
3. Лидия, 56 — ★★★★★ Очень удобно для меня, спасибо."""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEBWjdZ2AFss5xKwQJan-OuPo8cZS0AALd_jEbkOvpSpFD-iw9jQuHAQADAgADeQADNgQ', caption=offer1)
    
    # Офер 2 (3 отзыва с фото)
    offer2 = """Офер 2:
4. Оксана, 41 — ★★★★★ Глажка — не мой конёк, теперь всё за меня делают, спасибо!!!
5. Павел, 37 — ★★★★★ Приятно удивлён качеством и скоростью.
6. ★★★★★ Быстро и идеально!"""
    await message.answer_photo(photo='AgACAgIAAxkBAAIEB2jdZ3cnQwAB1nqVx_3qOiNdK0bGygAC4f4xG5Dr6UogN6n-4DG-ggEAAwIAA3kAAzYE', caption=offer2)
    
    # Офер 3 (3 отзыва с фото)
    offer3 = """Офер 3:
7. ★★★★★ Лучший сервис!
8. ★★★★★ Вещи — огонь!
9. ★★★★★ Идеально"""
    await message.answer_photo(photo='AgACAgIAAxkBAAIECWjdZ4ci5UEa6lInky19EpffuZORAALj_jEbkOvpSilMEP3byErwAQADAgADeQADNgQ', caption=offer3)
    
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
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать заказ", callback_data="make_order")],
        [InlineKeyboardButton(text="Задать вопрос", callback_data="support")],
    ])
    
    # Отправка фото с подписью и клавиатурой в одном сообщении
    await message.answer_photo(
        photo='AgACAgIAAxkBAAIED2jdZ-20723XKulmd-KCeY9ebsV3AALr_jEbkOvpSg1Zsk6-nJcNAQADAgADeQADNgQ',
        caption=text,
        reply_markup=keyboard
    )
# Техподдержка
async def handle_support(message: types.Message):
    text = "Пока можешь направить вопрос основателю проекта"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать основателю", url="https://t.me/OlegMahalov")],
    ])
    await message.answer(text, reply_markup=keyboard)

# Хэндлер для обработки фотографий и видео
@dp.message()
async def handle_photo_or_video(message: types.Message):
    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        await message.answer(f"Получен file_id: {file_id}")
        logging.info(f"Получен file_id: {file_id}")
    if message.video:
        video = message.video
        file_id = video.file_id
        await message.answer(f"Получен video file_id: {file_id}")
        logging.info(f"Получен video file_id: {file_id}")

# Проверка примечаний от менеджеров в amoCRM
async def check_amocrm_notes():
    while True:
        try:
            # Получаем timestamp последней проверки
            last_check = amocrm_client.tokens.get('last_check_timestamp')
            current_time = int(datetime.now().timestamp())
            
            # Если это первая проверка, берем последние 5 минут
            if not last_check:
                last_check = current_time - 300
            
            # Проверяем все активные заказы
            for user_id, order_data in orders.items():
                lead_id = order_data.get('amocrm_lead_id')
                if not lead_id:
                    continue
                
                # Получаем новые примечания
                notes = await amocrm_client.get_lead_notes(lead_id, last_check)
                
                for note in notes:
                    # Проверяем, что это текстовое примечание от менеджера
                    if note.get('note_type') == 'common' and note.get('text'):
                        note_text = note.get('text', '')
                        # Исключаем системные сообщения и сообщения от бота
                        if not any(keyword in note_text.lower() for keyword in ['telegram id:', 'заказ создан', 'система']):
                            try:
                                await bot.send_message(
                                    user_id, 
                                    f"💬 Сообщение от менеджера:\n\n{note_text}"
                                )
                                logging.info(f"Отправлено сообщение от менеджера пользователю {user_id}: {note_text[:50]}...")
                            except Exception as e:
                                logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            
            # Обновляем timestamp последней проверки
            amocrm_client.tokens['last_check_timestamp'] = current_time
            amocrm_client.save_tokens()
            
        except Exception as e:
            logging.error(f"Ошибка при проверке примечаний amoCRM: {e}")
        
        # Ждем 60 секунд перед следующей проверкой
        await asyncio.sleep(60)

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

# Функция для тестирования токена
async def test_bot_token():
    try:
        logging.info("Тестирование токена бота...")
        me = await bot.get_me()
        logging.info(f"✅ Токен действителен! Бот: @{me.username} ({me.first_name})")
        return True
    except Exception as e:
        logging.error(f"❌ Ошибка токена: {e}")
        return False

# Запуск
async def main():
    try:
        # Тестируем токен бота
        if not await test_bot_token():
            raise SystemExit("Токен бота недействителен. Проверьте токен через @BotFather.")
        
        # Инициализация amoCRM
        logging.info("Инициализация amoCRM...")
        amocrm_client.validate_tokens()
        await amocrm_client.get_account_info()
        await amocrm_client.get_pipeline_stages(amocrm_client.tokens['pipeline_id'])
        logging.info("AmoCRM инициализирован успешно")
        
        # Запуск фоновых задач
        inactive_task = asyncio.create_task(check_inactive_users())
        amocrm_task = asyncio.create_task(check_amocrm_notes())
        
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Получен запрос на остановку бота. Выполняется graceful shutdown...")
        await asyncio.sleep(5)
        await bot.close()
        await amocrm_client.close_session()
        
        # Останавливаем фоновые задачи
        tasks_to_cancel = [inactive_task, amocrm_task]
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logging.info(f"Фоновое задание {task.get_name()} успешно остановлено.")
    except Exception as e:
        logging.error(f"Ошибка при запуске поллинга: {e}")
        if "Unauthorized" in str(e):
            logging.error("Ошибка авторизации: токен недействителен или бот заблокирован")
            logging.error("Проверьте токен через @BotFather в Telegram")
        raise SystemExit("Не удалось запустить бота. Проверьте токен и соединение.")
    finally:
        await asyncio.sleep(5)
        await bot.close()
        await amocrm_client.close_session()
        logging.info("Бот остановлен.")

if __name__ == '__main__':
    asyncio.run(main())
