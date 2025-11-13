import telebot
from telebot import types
import json
import os
from datetime import datetime
import time

# Bot tokenini kiriting
BOT_TOKEN = '7956388141:AAEx0dZKvXV0qjtBcNhGF3FUfSOxNEHfykg'
bot = telebot.TeleBot(BOT_TOKEN)

# Admin IDlar
ADMIN_IDS = [6311751656]  # O'z Telegram ID'ingizni kiriting

# Ma'lumotlar bazasi fayllari
MOVIES_FILE = 'movies_data.json'
USERS_FILE = 'users_data.json'
CATEGORIES_FILE = 'categories_data.json'

# Asosiy kategoriyalar (hard-coded)
DEFAULT_CATEGORIES = {
    'motivatsiya': {'name': 'Motivatsiya', 'emoji': '💡', 'order': 1},
    'ilmiy_fantastik': {'name': 'Ilmiy va Fantastik', 'emoji': '🔬', 'order': 2},
    'computer_science': {'name': 'Computer Science', 'emoji': '💻', 'order': 3}
}

# Emoji va belgilar
EMOJI = {
    'movie': '🎬',
    'search': '🔍',
    'list': '📋',
    'add': '➕',
    'download': '📥',
    'info': 'ℹ️',
    'star': '⭐',
    'calendar': '📅',
    'category': '🗂',
    'genre': '🎭',
    'description': '📝',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'admin': '👑',
    'user': '👤',
    'stats': '📊',
    'settings': '⚙️',
    'back': '◀️'
}

# Ma'lumotlarni yuklash
def load_data(filename, default=None):
    """Ma'lumotlarni JSON fayldan yuklash"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ {filename} yuklashda xatolik: {e}")
            return default if default is not None else {}
    return default if default is not None else {}

def save_data(data, filename):
    """Ma'lumotlarni JSON faylga saqlash"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ {filename} saqlashda xatolik: {e}")
        return False

# Global o'zgaruvchilar
movies_db = load_data(MOVIES_FILE)
users_db = load_data(USERS_FILE)
categories_db = load_data(CATEGORIES_FILE, DEFAULT_CATEGORIES.copy())

# Agar kategoriyalar bo'sh bo'lsa, default kategoriyalarni qo'shish
if not categories_db:
    categories_db = DEFAULT_CATEGORIES.copy()
    save_data(categories_db, CATEGORIES_FILE)

temp_data = {}

# MUHIM: Eski movies_db'dagi kinolarni yangi formatga o'tkazish
def migrate_old_movies():
    """Eski formatdagi kinolarni yangi formatga o'tkazish"""
    changed = False
    for code, movie in movies_db.items():
        # Agar category_id yo'q bo'lsa, category'dan yaratish
        if 'category_id' not in movie and 'category' in movie:
            cat_name = movie['category']
            # Kategoriya ID topish yoki yaratish
            cat_id = None
            for cid, cinfo in categories_db.items():
                if cinfo['name'] == cat_name:
                    cat_id = cid
                    break
            
            # Agar topilmasa, default kategoriyaga qo'yish
            if not cat_id:
                # Eng yaqin kategoriyani topish
                if 'motiv' in cat_name.lower() or 'ilhom' in cat_name.lower():
                    cat_id = 'motivatsiya'
                elif 'ilmiy' in cat_name.lower() or 'fant' in cat_name.lower() or 'bio' in cat_name.lower():
                    cat_id = 'ilmiy_fantastik'
                elif 'komputer' in cat_name.lower() or 'dastur' in cat_name.lower() or 'tech' in cat_name.lower():
                    cat_id = 'computer_science'
                else:
                    # Yangi kategoriya yaratish
                    cat_id = cat_name.lower().replace(' ', '_').replace('-', '_')
                    if cat_id not in categories_db:
                        categories_db[cat_id] = {
                            'name': cat_name,
                            'emoji': '📁',
                            'order': len(categories_db) + 1,
                            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        save_data(categories_db, CATEGORIES_FILE)
            
            movies_db[code]['category_id'] = cat_id
            changed = True
    
    if changed:
        save_data(movies_db, MOVIES_FILE)
        print(f"✅ {len(movies_db)} ta kino yangi formatga o'tkazildi")

# Dastur boshlanishida migratsiya qilish
migrate_old_movies()

# Foydalanuvchini ro'yxatdan o'tkazish
def register_user(user):
    """Foydalanuvchini tizimga qo'shish"""
    user_id = str(user.id)
    if user_id not in users_db:
        users_db[user_id] = {
            'username': user.username,
            'first_name': user.first_name,
            'joined': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'searches': 0,
            'downloads': 0
        }
        save_data(users_db, USERS_FILE)
        return True
    return False

# Kategoriya ID yaratish
def generate_category_id(name):
    """Kategoriya nomi uchun ID yaratish"""
    return name.lower().replace(' ', '_').replace('-', '_')

# Asosiy menyu tugmalari
def get_main_menu(user_id):
    """Asosiy menyu tugmalarini yaratish"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn_search = types.KeyboardButton(f'{EMOJI["search"]} Kino qidirish')
    btn_list = types.KeyboardButton(f'{EMOJI["list"]} Kinolar ro\'yxati')
    btn_info = types.KeyboardButton(f'{EMOJI["info"]} Bot haqida')
    
    markup.add(btn_search, btn_list)
    markup.add(btn_info)
    
    if user_id in ADMIN_IDS:
        btn_admin = types.KeyboardButton(f'{EMOJI["admin"]} Admin panel')
        markup.add(btn_admin)
    
    return markup

# /start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    """Bot ishga tushganda birinchi xabar"""
    is_new = register_user(message.from_user)
    
    welcome_text = f"""
{EMOJI['movie']} <b>Kino Bot'ga xush kelibsiz!</b>

{'🎉 Yangi foydalanuvchi!' if is_new else 'Qaytganingizdan xursandmiz!'} {message.from_user.first_name}! 👋

Bu bot orqali eng sara motivatsion, ilmiy va texnologiya kinolarini topasiz!

<b>📚 Kategoriyalar:</b>
"""
    
    # Kategoriyalarni tartib bilan ko'rsatish
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    for cat_id, cat_info in sorted_cats:
        welcome_text += f"{cat_info.get('emoji', '📁')} {cat_info['name']}\n"
    
    welcome_text += f"""
<b>🎯 Qanday foydalanish:</b>
• 🔢 Kino kodini kiriting (masalan: M001)
• 🔍 Kino nomini yozing
• 📋 Menyu tugmalaridan foydalaning

Boshlash uchun pastdagi tugmalardan birini tanlang! 👇
"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='HTML',
        reply_markup=get_main_menu(message.from_user.id)
    )

# MUHIM FIX: Admin panel text handler - eng yuqorida bo'lishi kerak!
@bot.message_handler(func=lambda m: m.text and m.text == f'{EMOJI["admin"]} Admin panel')
def admin_panel(message):
    """Admin panel ko'rsatish"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, f"{EMOJI['error']} Sizda admin huquqi yo'q!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_add = types.InlineKeyboardButton(
        f"{EMOJI['add']} Kino qo'shish",
        callback_data='admin_add_movie'
    )
    btn_stats = types.InlineKeyboardButton(
        f"{EMOJI['stats']} Statistika",
        callback_data='admin_stats'
    )
    btn_categories = types.InlineKeyboardButton(
        f"{EMOJI['category']} Kategoriyalar",
        callback_data='admin_categories'
    )
    btn_users = types.InlineKeyboardButton(
        f"{EMOJI['user']} Foydalanuvchilar",
        callback_data='admin_users'
    )
    
    markup.add(btn_add, btn_stats)
    markup.add(btn_categories, btn_users)
    
    admin_text = f"""
{EMOJI['admin']} <b>Admin Panel</b>

📊 <b>Umumiy statistika:</b>
{EMOJI['movie']} Kinolar: {len(movies_db)} ta
{EMOJI['user']} Foydalanuvchilar: {len(users_db)} ta
{EMOJI['category']} Kategoriyalar: {len(categories_db)} ta

Kerakli bo'limni tanlang:
"""
    
    bot.send_message(
        message.chat.id,
        admin_text,
        parse_mode='HTML',
        reply_markup=markup
    )

# KATEGORIYALAR BOSHQARUVI
@bot.callback_query_handler(func=lambda call: call.data == 'admin_categories')
def manage_categories(call):
    """Kategoriyalarni boshqarish"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Mavjud kategoriyalar
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    
    categories_text = f"""
{EMOJI['category']} <b>Kategoriyalar boshqaruvi</b>

<b>Mavjud kategoriyalar:</b> {len(categories_db)} ta

"""
    
    for cat_id, cat_info in sorted_cats:
        categories_text += f"{cat_info.get('emoji', '📁')} {cat_info['name']}\n"
        
        # Har bir kategoriya uchun o'chirish tugmasi (default kategoriyalar bundan mustasno)
        if cat_id not in DEFAULT_CATEGORIES:
            btn = types.InlineKeyboardButton(
                f"🗑 {cat_info['name']} ni o'chirish",
                callback_data=f"delcat_{cat_id}"
            )
            markup.add(btn)
    
    # Yangi kategoriya qo'shish
    btn_add = types.InlineKeyboardButton(
        f"{EMOJI['add']} Yangi kategoriya qo'shish",
        callback_data='admin_add_category'
    )
    btn_back = types.InlineKeyboardButton(
        f"{EMOJI['back']} Orqaga",
        callback_data='back_to_admin'
    )
    
    markup.add(btn_add)
    markup.add(btn_back)
    
    try:
        bot.edit_message_text(
            categories_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            categories_text,
            parse_mode='HTML',
            reply_markup=markup
        )

# Yangi kategoriya qo'shish
@bot.callback_query_handler(func=lambda call: call.data == 'admin_add_category')
def add_category_prompt(call):
    """Yangi kategoriya qo'shish so'rovi"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(
        call.message.chat.id,
        f"""
{EMOJI['add']} <b>Yangi kategoriya qo'shish</b>

Quyidagi formatda ma'lumot yuboring:

<code>KATEGORIYA_NOMI|EMOJI</code>

<b>Namuna:</b>
<code>Tarixiy filmlar|🏛</code>
<code>Komediya|😂</code>
<code>Jangari|⚔️</code>

<i>Emoji ixtiyoriy - agar yozmasangiz, avtomatik 📁 qo'yiladi</i>

Bekor qilish: /cancel
""",
        parse_mode='HTML'
    )
    
    bot.register_next_step_handler(msg, process_new_category)

def process_new_category(message):
    """Yangi kategoriyani qo'shish"""
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "❌ Bekor qilindi", reply_markup=get_main_menu(message.from_user.id))
        return
    
    try:
        parts = message.text.split('|')
        if len(parts) < 1:
            raise ValueError("Noto'g'ri format")
        
        category_name = parts[0].strip()
        category_emoji = parts[1].strip() if len(parts) > 1 else '📁'
        
        # Kategoriya ID yaratish
        cat_id = generate_category_id(category_name)
        
        # Kategoriya allaqachon mavjudligini tekshirish
        if cat_id in categories_db:
            bot.send_message(
                message.chat.id,
                f"{EMOJI['error']} Bu kategoriya allaqachon mavjud!\n\nQaytadan boshqa nom bilan urinib ko'ring.",
                reply_markup=get_main_menu(message.from_user.id)
            )
            return
        
        # Yangi kategoriya qo'shish
        categories_db[cat_id] = {
            'name': category_name,
            'emoji': category_emoji,
            'order': len(categories_db) + 1,
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        save_data(categories_db, CATEGORIES_FILE)
        
        success_msg = f"""
{EMOJI['success']} <b>Kategoriya muvaffaqiyatli qo'shildi!</b>

{category_emoji} <b>Nomi:</b> {category_name}
🆔 <b>ID:</b> {cat_id}

Endi kinolar qo'shishda bu kategoriyani tanlashingiz mumkin!
"""
        
        bot.send_message(
            message.chat.id,
            success_msg,
            parse_mode='HTML',
            reply_markup=get_main_menu(message.from_user.id)
        )
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['error']} Xatolik: {str(e)}\n\nQaytadan urinib ko'ring.",
            reply_markup=get_main_menu(message.from_user.id)
        )

# Kategoriyani o'chirish
@bot.callback_query_handler(func=lambda call: call.data.startswith('delcat_'))
def delete_category_confirm(call):
    """Kategoriyani o'chirish tasdiqi"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    cat_id = call.data.replace('delcat_', '')
    
    # Default kategoriyalarni o'chirib bo'lmaydi
    if cat_id in DEFAULT_CATEGORIES:
        bot.answer_callback_query(
            call.id,
            "❌ Default kategoriyalarni o'chirib bo'lmaydi!",
            show_alert=True
        )
        return
    
    if cat_id not in categories_db:
        bot.answer_callback_query(call.id, "❌ Kategoriya topilmadi!", show_alert=True)
        return
    
    # Kategoriyada kinolar borligini tekshirish
    movies_in_cat = sum(1 for movie in movies_db.values() if movie.get('category_id') == cat_id)
    
    markup = types.InlineKeyboardMarkup()
    btn_confirm = types.InlineKeyboardButton(
        "✅ Ha, o'chirish",
        callback_data=f"delcat_confirm_{cat_id}"
    )
    btn_cancel = types.InlineKeyboardButton(
        "❌ Yo'q, bekor qilish",
        callback_data='admin_categories'
    )
    markup.add(btn_confirm, btn_cancel)
    
    warning_text = f"""
{EMOJI['warning']} <b>Kategoriyani o'chirish tasdiqi</b>

Kategoriya: {categories_db[cat_id]['emoji']} {categories_db[cat_id]['name']}
Bu kategoriyada: {movies_in_cat} ta kino

⚠️ <b>Diqqat:</b> Kategoriya o'chirilsa, undagi barcha kinolar "Motivatsiya" kategoriyasiga o'tkaziladi.

Davom etasizmi?
"""
    
    bot.edit_message_text(
        warning_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delcat_confirm_'))
def delete_category(call):
    """Kategoriyani o'chirish"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    cat_id = call.data.replace('delcat_confirm_', '')
    
    if cat_id in categories_db:
        cat_name = categories_db[cat_id]['name']
        
        # Bu kategoriyaga tegishli kinolarni "motivatsiya" ga o'tkazish
        for movie_code in movies_db:
            if movies_db[movie_code].get('category_id') == cat_id:
                movies_db[movie_code]['category_id'] = 'motivatsiya'
                movies_db[movie_code]['category'] = 'Motivatsiya'
        
        save_data(movies_db, MOVIES_FILE)
        
        # Kategoriyani o'chirish
        del categories_db[cat_id]
        save_data(categories_db, CATEGORIES_FILE)
        
        bot.answer_callback_query(call.id, f"✅ {cat_name} kategoriyasi o'chirildi!", show_alert=True)
        
        # Kategoriyalar ro'yxatiga qaytish
        manage_categories(call)
    else:
        bot.answer_callback_query(call.id, "❌ Kategoriya topilmadi!", show_alert=True)

# Admin panelga qaytish
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_admin')
def back_to_admin(call):
    """Admin panelga qaytish"""
    if call.from_user.id not in ADMIN_IDS:
        return
    
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_add = types.InlineKeyboardButton(
        f"{EMOJI['add']} Kino qo'shish",
        callback_data='admin_add_movie'
    )
    btn_stats = types.InlineKeyboardButton(
        f"{EMOJI['stats']} Statistika",
        callback_data='admin_stats'
    )
    btn_categories = types.InlineKeyboardButton(
        f"{EMOJI['category']} Kategoriyalar",
        callback_data='admin_categories'
    )
    btn_users = types.InlineKeyboardButton(
        f"{EMOJI['user']} Foydalanuvchilar",
        callback_data='admin_users'
    )
    
    markup.add(btn_add, btn_stats)
    markup.add(btn_categories, btn_users)
    
    admin_text = f"""
{EMOJI['admin']} <b>Admin Panel</b>

📊 <b>Umumiy statistika:</b>
{EMOJI['movie']} Kinolar: {len(movies_db)} ta
{EMOJI['user']} Foydalanuvchilar: {len(users_db)} ta
{EMOJI['category']} Kategoriyalar: {len(categories_db)} ta

Kerakli bo'limni tanlang:
"""
    
    try:
        bot.edit_message_text(
            admin_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except:
        pass

# KINO QO'SHISH
@bot.callback_query_handler(func=lambda call: call.data == 'admin_add_movie')
def start_add_movie(call):
    """Kino qo'shishni boshlash"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    # Kategoriyalar ro'yxatini ko'rsatish
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    
    for cat_id, cat_info in sorted_cats:
        btn = types.InlineKeyboardButton(
            f"{cat_info.get('emoji', '📁')} {cat_info['name']}",
            callback_data=f"addmovie_cat_{cat_id}"
        )
        markup.add(btn)
    
    btn_cancel = types.InlineKeyboardButton(
        "❌ Bekor qilish",
        callback_data='back_to_admin'
    )
    markup.add(btn_cancel)
    
    bot.edit_message_text(
        f"""
{EMOJI['add']} <b>Yangi kino qo'shish</b>

Birinchi, kino kategoriyasini tanlang:
""",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('addmovie_cat_'))
def add_movie_category_selected(call):
    """Kategoriya tanlangandan keyin"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    cat_id = call.data.replace('addmovie_cat_', '')
    
    if cat_id not in categories_db:
        bot.answer_callback_query(call.id, "❌ Kategoriya topilmadi!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    # Tanlangan kategoriyani saqlash
    temp_data[call.from_user.id] = {'category_id': cat_id}
    
    category_name = categories_db[cat_id]['name']
    
    msg = bot.send_message(
        call.message.chat.id,
        f"""
{EMOJI['add']} <b>Yangi kino qo'shish</b>
{EMOJI['category']} <b>Kategoriya:</b> {categories_db[cat_id]['emoji']} {category_name}

Endi quyidagi formatda kino ma'lumotlarini yuboring:

<code>KOD|NOM|YIL|JANR|TAVSIF</code>

<b>Namuna:</b>
<code>M001|The Pursuit of Happyness|2006|Drama, Biography|Chris Gardner haqida hayotini o'zgartirgan motivatsion film. Oila, kurash va muvaffaqiyat haqida.</code>

<i>💡 Tavsif: Kino haqida batafsil ma'lumot, 2-3 jumla</i>

Bekor qilish: /cancel
""",
        parse_mode='HTML'
    )
    
    bot.register_next_step_handler(msg, process_movie_info)

def process_movie_info(message):
    """Kino ma'lumotlarini qayta ishlash"""
    if message.text == '/cancel':
        bot.send_message(
            message.chat.id,
            "❌ Bekor qilindi",
            reply_markup=get_main_menu(message.from_user.id)
        )
        if message.from_user.id in temp_data:
            del temp_data[message.from_user.id]
        return
    
    try:
        parts = message.text.split('|')
        if len(parts) != 5:
            raise ValueError("Noto'g'ri format - 5 ta qism bo'lishi kerak")
        
        code, title, year, genre, description = [p.strip() for p in parts]
        
        # Kod formati tekshiruvi
        code = code.upper()
        
        # Kod allaqachon mavjudligini tekshirish
        if code in movies_db:
            bot.send_message(
                message.chat.id,
                f"{EMOJI['error']} Bu kod allaqachon mavjud: {code}\n\nBoshqa kod bilan urinib ko'ring."
            )
            bot.register_next_step_handler(message, process_movie_info)
            return
        
        # Ma'lumotlarni saqlash
        user_data = temp_data.get(message.from_user.id, {})
        cat_id = user_data.get('category_id', 'motivatsiya')
        
        temp_data[message.from_user.id] = {
            'code': code,
            'title': title,
            'year': year,
            'genre': genre,
            'category_id': cat_id,
            'category': categories_db.get(cat_id, {}).get('name', 'Motivatsiya'),
            'description': description
        }
        
        cat_info = categories_db.get(cat_id, {})
        
        preview = f"""
{EMOJI['success']} <b>Ma'lumotlar qabul qilindi!</b>

{EMOJI['movie']} <b>Nomi:</b> {title}
{EMOJI['calendar']} <b>Yili:</b> {year}
{EMOJI['genre']} <b>Janr:</b> {genre}
{EMOJI['category']} <b>Kategoriya:</b> {cat_info.get('emoji', '📁')} {cat_info.get('name', 'Motivatsiya')}
{EMOJI['description']} <b>Tavsif:</b> {description}
🔢 <b>Kod:</b> {code}

✅ Ajoyib! Endi kino video faylini yuboring:
<i>(Telegram orqali to'g'ridan-to'g'ri video yuklang)</i>
"""
        
        msg = bot.send_message(message.chat.id, preview, parse_mode='HTML')
        bot.register_next_step_handler(msg, process_movie_file)
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['error']} Xatolik: {str(e)}\n\nQaytadan to'g'ri formatda yuboring!"
        )
        bot.register_next_step_handler(message, process_movie_info)

def process_movie_file(message):
    """Video faylni qayta ishlash"""
    user_id = message.from_user.id
    
    if message.text == '/cancel':
        bot.send_message(
            message.chat.id,
            "❌ Bekor qilindi",
            reply_markup=get_main_menu(message.from_user.id)
        )
        if user_id in temp_data:
            del temp_data[user_id]
        return
    
    if user_id not in temp_data:
        bot.reply_to(
            message,
            f"{EMOJI['error']} Ma'lumotlar topilmadi. Qaytadan /start dan boshlang."
        )
        return
    
    if message.content_type == 'video':
        # Loading xabari
        processing_msg = bot.send_message(
            message.chat.id,
            f"{EMOJI['success']} Video qabul qilindi! Qayta ishlanmoqda..."
        )
        
        file_id = message.video.file_id
        data = temp_data[user_id]
        
        # Kinoni bazaga qo'shish
        movies_db[data['code']] = {
            'title': data['title'],
            'year': data['year'],
            'genre': data['genre'],
            'category_id': data['category_id'],
            'category': data['category'],
            'description': data['description'],
            'file_id': file_id,
            'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'views': 0,
            'downloads': 0
        }
        
        save_data(movies_db, MOVIES_FILE)
        
        # Processing xabarini o'chirish
        try:
            bot.delete_message(message.chat.id, processing_msg.message_id)
        except:
            pass
        
        cat_info = categories_db.get(data['category_id'], {})
        
        success_msg = f"""
{EMOJI['success']} <b>Kino muvaffaqiyatli qo'shildi!</b>

{EMOJI['movie']} <b>{data['title']}</b> ({data['year']})
{EMOJI['category']} {cat_info.get('emoji', '📁')} {data['category']}
🔢 Kod: <code>{data['code']}</code>

Foydalanuvchilar endi bu kinoni kod yoki nom orqali topib tomosha qilishlari mumkin!

Yana kino qo'shish: {EMOJI['admin']} Admin panel
"""
        
        bot.send_message(
            message.chat.id,
            success_msg,
            parse_mode='HTML',
            reply_markup=get_main_menu(message.from_user.id)
        )
        
        del temp_data[user_id]
        
    else:
        bot.reply_to(
            message,
            f"{EMOJI['error']} Iltimos, faqat video fayl yuboring!\n\nBekor qilish: /cancel"
        )
        bot.register_next_step_handler(message, process_movie_file)

# MUHIM FIX: Kinolar ro'yxati - Bu yerda kategoriyalar to'g'ri ko'rsatilishi kerak
@bot.message_handler(func=lambda m: m.text and m.text == f'{EMOJI["list"]} Kinolar ro\'yxati')
def show_movies_list(message):
    """Barcha kinolar ro'yxatini ko'rsatish"""
    if not movies_db:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['warning']} Hozircha kinolar mavjud emas."
        )
        return
    
    # Kategoriyalar bo'yicha guruhlash
    categories_count = {}
    for code, movie in movies_db.items():
        cat_id = movie.get('category_id', 'motivatsiya')
        if cat_id not in categories_count:
            categories_count[cat_id] = 0
        categories_count[cat_id] += 1
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Kategoriyalarni tartib bilan ko'rsatish
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    
    has_movies = False
    for cat_id, cat_info in sorted_cats:
        count = categories_count.get(cat_id, 0)
        if count > 0:  # Faqat kinolari bor kategoriyalarni ko'rsatish
            btn = types.InlineKeyboardButton(
                f"{cat_info.get('emoji', '📁')} {cat_info['name']} ({count})",
                callback_data=f"cat_{cat_id}"
            )
            markup.add(btn)
            has_movies = True
    
    if not has_movies:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['warning']} Hozircha kinolar mavjud emas yoki kategoriyalarga biriktirilmagan.",
            reply_markup=get_main_menu(message.from_user.id)
        )
        return
    
    bot.send_message(
        message.chat.id,
        f"""
{EMOJI['list']} <b>Kinolar ro'yxati</b>

📊 Jami kinolar: <b>{len(movies_db)}</b> ta
{EMOJI['category']} Kategoriyalar: <b>{len(categories_count)}</b> ta

Kategoriyani tanlang:
""",
        parse_mode='HTML',
        reply_markup=markup
    )

# KATEGORIYA BO'YICHA KINOLAR
@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def show_category_movies(call):
    """Tanlangan kategoriya kinolarini ko'rsatish"""
    # IMPORTANT: Callback query ni darhol acknowledge qilish
    bot.answer_callback_query(call.id, "📥 Yuklanmoqda...")
    
    cat_id = call.data.replace('cat_', '')
    
    if cat_id not in categories_db:
        bot.answer_callback_query(call.id, "❌ Kategoriya topilmadi!", show_alert=True)
        return
    
    # Bu kategoriyaga tegishli kinolarni topish
    category_movies = []
    for code, movie in movies_db.items():
        if movie.get('category_id') == cat_id:
            category_movies.append((code, movie))
    
    if not category_movies:
        bot.answer_callback_query(call.id, "❌ Bu kategoriyada kinolar yo'q", show_alert=True)
        return
    
    # Kinolarni yil bo'yicha saralash (eng yangi birinchi)
    category_movies.sort(key=lambda x: x[1].get('year', '0'), reverse=True)
    
    cat_info = categories_db[cat_id]
    
    # Kinolar ro'yxatini yaratish
    movies_list_text = ""
    for code, movie in category_movies[:10]:  # Birinchi 10 ta
        movies_list_text += f"\n🎬 <code>{code}</code> - {movie['title']} ({movie['year']})"
    
    if len(category_movies) > 10:
        movies_list_text += f"\n\n<i>... va yana {len(category_movies) - 10} ta kino</i>"
    
    text = f"""
{cat_info.get('emoji', '📁')} <b>Kategoriya: {cat_info['name']}</b>

📊 Kinolar soni: {len(category_movies)} ta
{movies_list_text}

<i>💡 Kinoni tanlash uchun pastdagi tugmalardan foydalaning yoki kino kodini yuboring</i>
"""
    
    # Inline tugmalar - har bir kino uchun
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for code, movie in category_movies:
        title_short = movie['title'][:30] + "..." if len(movie['title']) > 30 else movie['title']
        btn = types.InlineKeyboardButton(
            f"🎬 {title_short} ({movie['year']})",
            callback_data=f"movie_{code}"
        )
        markup.add(btn)
    
    btn_back = types.InlineKeyboardButton(
        f"{EMOJI['back']} Orqaga",
        callback_data="back_to_categories"
    )
    markup.add(btn_back)
    
    # Xabarni yangilash
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except Exception as e:
        # Agar xabar bir xil bo'lsa, yangi xabar yuborish
        print(f"Edit error: {e}")
        bot.send_message(
            call.message.chat.id,
            text,
            parse_mode='HTML',
            reply_markup=markup
        )

# Orqaga qaytish
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_categories')
def back_to_categories(call):
    """Kategoriyalar ro'yxatiga qaytish"""
    bot.answer_callback_query(call.id)
    
    # Kategoriyalar bo'yicha guruhlash
    categories_count = {}
    for code, movie in movies_db.items():
        cat_id = movie.get('category_id', 'motivatsiya')
        if cat_id not in categories_count:
            categories_count[cat_id] = 0
        categories_count[cat_id] += 1
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    
    for cat_id, cat_info in sorted_cats:
        count = categories_count.get(cat_id, 0)
        if count > 0:
            btn = types.InlineKeyboardButton(
                f"{cat_info.get('emoji', '📁')} {cat_info['name']} ({count})",
                callback_data=f"cat_{cat_id}"
            )
            markup.add(btn)
    
    try:
        bot.edit_message_text(
            f"""
{EMOJI['list']} <b>Kinolar ro'yxati</b>

📊 Jami kinolar: <b>{len(movies_db)}</b> ta
{EMOJI['category']} Kategoriyalar: <b>{len(categories_count)}</b> ta

Kategoriyani tanlang:
""",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except:
        pass

# KINO MA'LUMOTLARINI KO'RSATISH
@bot.callback_query_handler(func=lambda call: call.data.startswith('movie_'))
def show_movie_info(call):
    """Tanlangan kino haqida ma'lumot"""
    bot.answer_callback_query(call.id, "📥 Yuklanmoqda...")
    
    code = call.data.replace('movie_', '')
    
    if code not in movies_db:
        bot.answer_callback_query(call.id, "❌ Kino topilmadi!", show_alert=True)
        return
    
    movie = movies_db[code]
    cat_id = movie.get('category_id', 'motivatsiya')
    cat_info = categories_db.get(cat_id, {'name': 'Motivatsiya', 'emoji': '📁'})
    
    info_text = f"""
{EMOJI['movie']} <b>{movie['title']}</b>

{EMOJI['calendar']} <b>Yili:</b> {movie['year']}
{EMOJI['genre']} <b>Janr:</b> {movie['genre']}
{EMOJI['category']} <b>Kategoriya:</b> {cat_info.get('emoji', '📁')} {cat_info['name']}

{EMOJI['description']} <b>Tavsif:</b>
{movie['description']}

🔢 <b>Kod:</b> <code>{code}</code>
👁 <b>Ko'rilgan:</b> {movie.get('views', 0)} marta
📥 <b>Yuklangan:</b> {movie.get('downloads', 0)} marta

<i>💡 Kinoni tomosha qilish uchun "📥 Yuklab olish" tugmasini bosing</i>
"""
    
    markup = types.InlineKeyboardMarkup()
    btn_download = types.InlineKeyboardButton(
        f"{EMOJI['download']} Yuklab olish",
        callback_data=f"download_{code}"
    )
    btn_back = types.InlineKeyboardButton(
        f"{EMOJI['back']} Orqaga",
        callback_data=f"cat_{cat_id}"
    )
    markup.add(btn_download)
    markup.add(btn_back)
    
    try:
        bot.edit_message_text(
            info_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except Exception as e:
        print(f"Edit error: {e}")
        bot.send_message(
            call.message.chat.id,
            info_text,
            parse_mode='HTML',
            reply_markup=markup
        )

# KINO YUKLAB OLISH
@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
def download_movie(call):
    """Kinoni yuborish"""
    code = call.data.replace('download_', '')
    
    if code not in movies_db:
        bot.answer_callback_query(call.id, "❌ Kino topilmadi!", show_alert=True)
        return
    
    movie = movies_db[code]
    bot.answer_callback_query(call.id, "📥 Kino yuklanmoqda...")
    
    # Ko'rishlar va yuklab olishlar sonini oshirish
    movies_db[code]['views'] = movies_db[code].get('views', 0) + 1
    movies_db[code]['downloads'] = movies_db[code].get('downloads', 0) + 1
    save_data(movies_db, MOVIES_FILE)
    
    if movie.get('file_id'):
        try:
            # Kategoriya ma'lumotlari
            cat_id = movie.get('category_id', 'motivatsiya')
            cat_info = categories_db.get(cat_id, {'name': 'Motivatsiya', 'emoji': '📁'})
            
            # MUHIM: Caption ichida to'liq tavsif
            caption = f"""
{EMOJI['movie']} <b>{movie['title']}</b> ({movie['year']})

{EMOJI['genre']} <b>Janr:</b> {movie['genre']}
{EMOJI['category']} <b>Kategoriya:</b> {cat_info.get('emoji', '📁')} {cat_info['name']}

{EMOJI['description']} <b>Tavsif:</b>
{movie['description']}

🔢 Kod: <code>{code}</code>

━━━━━━━━━━━━━━━━━━━
🤖 Bot: @valixonov04
💡 Ko'proq kinolar: {EMOJI['list']} Kinolar ro'yxati
"""
            
            # Videoni yuborish
            bot.send_video(
                call.message.chat.id,
                movie['file_id'],
                caption=caption,
                parse_mode='HTML',
                supports_streaming=True
            )
            
            # Foydalanuvchi statistikasini yangilash
            user_id = str(call.from_user.id)
            if user_id in users_db:
                users_db[user_id]['downloads'] = users_db[user_id].get('downloads', 0) + 1
                save_data(users_db, USERS_FILE)
            
            # Muvaffaqiyatli yuklangan xabar
            bot.send_message(
                call.message.chat.id,
                f"""
{EMOJI['success']} <b>Kino muvaffaqiyatli yuklandi!</b>

Yaxshi tomosha! 🍿

Yana kinolar izlash: {EMOJI['list']} Kinolar ro'yxati
""",
                parse_mode='HTML'
            )
            
        except Exception as e:
            print(f"Video yuborish xatoligi: {e}")
            bot.send_message(
                call.message.chat.id,
                f"{EMOJI['error']} Video yuborishda xatolik yuz berdi. Qaytadan urinib ko'ring.\n\n<i>Agar muammo takroran yuzaga kelsa, @valixonov04 ga murojaat qiling.</i>",
                parse_mode='HTML'
            )
    else:
        bot.send_message(
            call.message.chat.id,
            f"{EMOJI['error']} Video fayl topilmadi"
        )

# Kino qidirish
@bot.message_handler(func=lambda m: m.text and m.text == f'{EMOJI["search"]} Kino qidirish')
def search_movie_prompt(message):
    """Kino qidirish so'rovini olish"""
    msg = bot.send_message(
        message.chat.id,
        f"""
{EMOJI['search']} <b>Kino qidirish</b>

Kino kodi yoki nomini kiriting:

<b>Masalan:</b>
• M001
• Spider-Man
• Pursuit

<i>Bekor qilish: /cancel</i>
""",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, search_movie)

def search_movie(message):
    """Kinoni qidirish"""
    if message.text == '/cancel':
        bot.send_message(
            message.chat.id,
            "❌ Bekor qilindi",
            reply_markup=get_main_menu(message.from_user.id)
        )
        return
    
    query = message.text.strip().upper()
    
    # Avval kod bo'yicha qidirish
    if query in movies_db:
        show_movie_details(message, query)
        return
    
    # Keyin nom bo'yicha qidirish
    results = []
    query_lower = message.text.strip().lower()
    
    for code, movie in movies_db.items():
        # Nom yoki janr bo'yicha qidirish
        if (query_lower in movie['title'].lower() or 
            query_lower in movie.get('genre', '').lower() or
            query_lower in movie.get('description', '').lower()):
            results.append((code, movie))
    
    if results:
        if len(results) == 1:
            show_movie_details(message, results[0][0])
        else:
            # Ko'p natija bo'lsa, ro'yxat ko'rsatish
            results.sort(key=lambda x: x[1].get('year', '0'), reverse=True)
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for code, movie in results[:15]:  # Maksimal 15 ta
                cat_id = movie.get('category_id', 'motivatsiya')
                cat_info = categories_db.get(cat_id, {})
                
                btn_text = f"{movie['title']} ({movie['year']}) - {cat_info.get('emoji', '📁')} {cat_info.get('name', 'Motivatsiya')}"
                if len(btn_text) > 60:
                    btn_text = btn_text[:60] + "..."
                
                btn = types.InlineKeyboardButton(
                    btn_text,
                    callback_data=f"movie_{code}"
                )
                markup.add(btn)
            
            result_text = f"""
{EMOJI['search']} <b>Qidiruv natijalari</b>

"{message.text}" bo'yicha topildi: <b>{len(results)}</b> ta kino

Kerakli kinoni tanlang:
"""
            
            if len(results) > 15:
                result_text += f"\n<i>📌 Birinchi 15 ta natija ko'rsatildi</i>"
            
            bot.send_message(
                message.chat.id,
                result_text,
                parse_mode='HTML',
                reply_markup=markup
            )
        
        # Qidiruv statistikasini yangilash
        user_id = str(message.from_user.id)
        if user_id in users_db:
            users_db[user_id]['searches'] = users_db[user_id].get('searches', 0) + 1
            save_data(users_db, USERS_FILE)
    else:
        bot.send_message(
            message.chat.id,
            f"""
{EMOJI['error']} <b>Kino topilmadi</b>

"{message.text}" bo'yicha natija yo'q.

💡 <b>Maslahat:</b>
• Kino nomini to'liq yozing
• Yoki {EMOJI['list']} Kinolar ro'yxati orqali kategoriyalardan tanlang
• Kino kodini kiriting (masalan: M001)
""",
            parse_mode='HTML'
        )

def show_movie_details(message, code):
    """Kino tafsilotlarini ko'rsatish"""
    if code not in movies_db:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['error']} Kino topilmadi!"
        )
        return
    
    movie = movies_db[code]
    cat_id = movie.get('category_id', 'motivatsiya')
    cat_info = categories_db.get(cat_id, {'name': 'Motivatsiya', 'emoji': '📁'})
    
    info_text = f"""
{EMOJI['movie']} <b>{movie['title']}</b>

{EMOJI['calendar']} <b>Yili:</b> {movie['year']}
{EMOJI['genre']} <b>Janr:</b> {movie['genre']}
{EMOJI['category']} <b>Kategoriya:</b> {cat_info.get('emoji', '📁')} {cat_info['name']}

{EMOJI['description']} <b>Tavsif:</b>
{movie['description']}

🔢 <b>Kod:</b> <code>{code}</code>
👁 <b>Ko'rilgan:</b> {movie.get('views', 0)} marta

<i>💡 Kinoni tomosha qilish uchun "📥 Yuklab olish" tugmasini bosing</i>
"""
    
    markup = types.InlineKeyboardMarkup()
    btn_download = types.InlineKeyboardButton(
        f"{EMOJI['download']} Yuklab olish",
        callback_data=f"download_{code}"
    )
    markup.add(btn_download)
    
    bot.send_message(
        message.chat.id,
        info_text,
        parse_mode='HTML',
        reply_markup=markup
    )

# Bot haqida
@bot.message_handler(func=lambda m: m.text and m.text == f'{EMOJI["info"]} Bot haqida')
def bot_info(message):
    """Bot haqida ma'lumot"""
    
    # Kategoriyalar ro'yxati
    cat_list = ""
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    for cat_id, cat_info in sorted_cats:
        cat_list += f"{cat_info.get('emoji', '📁')} {cat_info['name']}\n"
    
    info_text = f"""
{EMOJI['info']} <b>Bot haqida</b>

Bu bot orqali siz minglab motivatsion, ilmiy va texnologiya kinolarini topib tomosha qilishingiz mumkin.

📊 <b>Statistika:</b>
{EMOJI['movie']} Kinolar: {len(movies_db)} ta
{EMOJI['category']} Kategoriyalar: {len(categories_db)} ta
{EMOJI['user']} Foydalanuvchilar: {len(users_db)} ta

📚 <b>Kategoriyalar:</b>
{cat_list}

<b>🎯 Imkoniyatlar:</b>
• Kino qidirish (kod yoki nom bo'yicha)
• Kategoriyalar bo'yicha ko'rish
• HD sifatda tomosha qilish
• Tezkor yuklab olish
• To'liq tavsif va ma'lumotlar

<b>💻 Ishlab chiquvchi:</b> @valixonov04
<b>📱 Versiya:</b> 2.1 (Fixed Edition)

<b>🆘 Yordam:</b> /help
"""
    
    bot.send_message(message.chat.id, info_text, parse_mode='HTML')

# Statistika (Admin)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def show_stats(call):
    """Statistikani ko'rsatish"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    total_views = sum(movie.get('views', 0) for movie in movies_db.values())
    total_downloads = sum(movie.get('downloads', 0) for movie in movies_db.values())
    
    # Kategoriyalar bo'yicha kinolar soni
    cat_stats = {}
    for movie in movies_db.values():
        cat_id = movie.get('category_id', 'motivatsiya')
        cat_stats[cat_id] = cat_stats.get(cat_id, 0) + 1
    
    stats_text = f"""
{EMOJI['stats']} <b>Bot statistikasi</b>

📊 <b>Umumiy:</b>
{EMOJI['movie']} Kinolar: {len(movies_db)} ta
{EMOJI['user']} Foydalanuvchilar: {len(users_db)} ta
{EMOJI['category']} Kategoriyalar: {len(categories_db)} ta
👁 Jami ko'rishlar: {total_views}
📥 Jami yuklanishlar: {total_downloads}

📚 <b>Kategoriyalar bo'yicha:</b>
"""
    
    sorted_cats = sorted(categories_db.items(), key=lambda x: x[1].get('order', 999))
    for cat_id, cat_info in sorted_cats:
        count = cat_stats.get(cat_id, 0)
        stats_text += f"{cat_info.get('emoji', '📁')} {cat_info['name']}: {count} ta\n"
    
    stats_text += "\n<b>🏆 Top 5 eng ko'p ko'rilgan kinolar:</b>\n"
    
    # Top 5 kino
    sorted_movies = sorted(
        movies_db.items(),
        key=lambda x: x[1].get('views', 0),
        reverse=True
    )[:5]
    
    for i, (code, movie) in enumerate(sorted_movies, 1):
        stats_text += f"{i}. {movie['title']} - {movie.get('views', 0)} 👁\n"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton(
        f"{EMOJI['back']} Orqaga",
        callback_data='back_to_admin'
    )
    markup.add(btn_back)
    
    try:
        bot.edit_message_text(
            stats_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except:
        bot.send_message(
            call.message.chat.id,
            stats_text,
            parse_mode='HTML',
            reply_markup=markup
        )

# Foydalanuvchilar ro'yxati (Admin)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_users')
def show_users(call):
    """Foydalanuvchilar ro'yxatini ko'rsatish"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    users_text = f"""
{EMOJI['user']} <b>Foydalanuvchilar ro'yxati</b>

Jami: {len(users_db)} ta foydalanuvchi

<b>Oxirgi 10 ta foydalanuvchi:</b>

"""
    
    # Oxirgi qo'shilganlarni birinchi ko'rsatish
    sorted_users = sorted(
        users_db.items(),
        key=lambda x: x[1].get('joined', ''),
        reverse=True
    )[:10]
    
    for user_id, user_data in sorted_users:
        username = user_data.get('username', 'Username yo\'q')
        first_name = user_data.get('first_name', 'Noma\'lum')
        joined = user_data.get('joined', 'Noma\'lum')
        searches = user_data.get('searches', 0)
        
        users_text += f"""
👤 <b>{first_name}</b> (@{username})
   🆔 ID: <code>{user_id}</code>
   📅 Qo'shilgan: {joined}
   🔍 Qidiruvlar: {searches}

"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton(
        f"{EMOJI['back']} Orqaga",
        callback_data='back_to_admin'
    )
    markup.add(btn_back)
    
    try:
        bot.edit_message_text(
            users_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except:
        bot.send_message(
            call.message.chat.id,
            users_text,
            parse_mode='HTML',
            reply_markup=markup
        )

# /help komandasi
@bot.message_handler(commands=['help'])
def help_command(message):
    """Yordam ko'rsatish"""
    help_text = f"""
{EMOJI['info']} <b>Yordam</b>

<b>🎯 Asosiy komandalar:</b>
/start - Botni ishga tushirish
/help - Yordam
/cancel - Amalni bekor qilish

<b>🔍 Kinolarni qidirish:</b>
1. {EMOJI['search']} Kino qidirish tugmasi
2. Kino kodini yozing (M001)
3. Kino nomini yozing

<b>📋 Kinolar ro'yxati:</b>
1. {EMOJI['list']} Kinolar ro'yxati tugmasi
2. Kategoriyani tanlang
3. Kinoni tanlang va yuklab oling

<b>👑 Admin funksiyalari:</b>
• Kino qo'shish
• Kategoriya qo'shish
• Statistika ko'rish
• Foydalanuvchilar ro'yxati

<b>💡 Maslahat:</b>
Eng tezkor yo'l - kino kodini to'g'ridan-to'g'ri yozish!

Savol yoki muammo bo'lsa: @valixonov04
"""
    
    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode='HTML'
    )

# MUHIM: Oddiy xabarlarni qayta ishlash - ENG OXIRDA BO'LISHI KERAK!
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Barcha boshqa xabarlarni qayta ishlash"""
    text = message.text.strip()
    code = text.upper()
    
    # Agar kod formatida bo'lsa
    if code in movies_db:
        show_movie_details(message, code)
    else:
        # Aks holda qidirish
        if len(text) >= 2:  # Kamida 2 ta harf
            search_movie(message)
        else:
            bot.reply_to(
                message,
                f"""
{EMOJI['warning']} Qidiruv uchun kamida 2 ta harf kiriting.

Yoki quyidagi tugmalardan foydalaning:
{EMOJI['list']} Kinolar ro'yxati
{EMOJI['search']} Kino qidirish
""",
                reply_markup=get_main_menu(message.from_user.id)
            )

# Botni ishga tushirish
if __name__ == '__main__':
    print("=" * 60)
    print(f"{EMOJI['success']} Bot ishga tushdi (Fixed Edition v2.1)")
    print(f"{EMOJI['movie']} Kinolar soni: {len(movies_db)}")
    print(f"{EMOJI['category']} Kategoriyalar: {len(categories_db)}")
    print(f"{EMOJI['user']} Foydalanuvchilar: {len(users_db)}")
    print("=" * 60)
    print("\n🚀 Bot ishlayapti... To'xtatish: Ctrl+C\n")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot to'xtatildi")
    except Exception as e:
        print(f"\n❌ Xatolik: {e}")
        print("🔄 Bot qayta ishga tushirilmoqda...\n")
        time.sleep(5)
        bot.polling(none_stop=True, interval=0, timeout=60)