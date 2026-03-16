import os
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq

# ========== CONFIG ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
groq_client = Groq(api_key=GROQ_API_KEY)

# ========== CLINIC DATA ==========
CLINIC = {
    "name": "MediCare Clinic",
    "tagline": "Your Health, Our Priority",
    "address": "456 Health Avenue, New York, NY 10002",
    "phone": "+1-212-555-0200",
    "email": "appointments@medicare-clinic.com",
    "hours": "Mon-Fri: 8AM-8PM | Sat: 9AM-5PM | Sun: Emergency Only",
    "emergency": "+1-911",
}

DOCTORS = {
    "D01": {
        "name": "Dr. Sarah Johnson",
        "specialty": "General Physician",
        "experience": "15 years",
        "fee": 80,
        "available": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
        "rating": 4.9,
        "about": "Experienced GP specializing in preventive care and chronic disease management"
    },
    "D02": {
        "name": "Dr. Michael Chen",
        "specialty": "Cardiologist",
        "experience": "20 years",
        "fee": 150,
        "available": ["Mon", "Wed", "Fri"],
        "slots": ["10:00 AM", "11:00 AM", "3:00 PM", "4:00 PM"],
        "rating": 4.8,
        "about": "Expert in heart disease, hypertension, and cardiovascular health"
    },
    "D03": {
        "name": "Dr. Emily Rodriguez",
        "specialty": "Dermatologist",
        "experience": "12 years",
        "fee": 120,
        "available": ["Tue", "Thu", "Sat"],
        "slots": ["9:00 AM", "10:30 AM", "12:00 PM", "2:30 PM"],
        "rating": 4.7,
        "about": "Specialist in skin conditions, cosmetic dermatology and hair treatments"
    },
    "D04": {
        "name": "Dr. James Wilson",
        "specialty": "Orthopedic",
        "experience": "18 years",
        "fee": 140,
        "available": ["Mon", "Tue", "Thu", "Fri"],
        "slots": ["8:00 AM", "9:00 AM", "2:00 PM", "3:00 PM", "5:00 PM"],
        "rating": 4.8,
        "about": "Expert in bone, joint and muscle conditions, sports injuries"
    },
    "D05": {
        "name": "Dr. Aisha Patel",
        "specialty": "Pediatrician",
        "experience": "10 years",
        "fee": 90,
        "available": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"],
        "rating": 4.9,
        "about": "Caring pediatrician for newborns to teenagers, vaccinations & development"
    },
}

SERVICES = [
    {"name": "General Checkup", "duration": "30 min", "fee": 80},
    {"name": "Blood Test", "duration": "15 min", "fee": 45},
    {"name": "X-Ray", "duration": "20 min", "fee": 120},
    {"name": "ECG", "duration": "20 min", "fee": 95},
    {"name": "Vaccination", "duration": "15 min", "fee": 35},
    {"name": "Health Screening Package", "duration": "2 hours", "fee": 250},
]

# Storage
user_bookings = {}
user_histories = {}
booking_data = {}

# ========== AI ==========
async def get_ai_response(user_id, message):
    if user_id not in user_histories:
        user_histories[user_id] = []

    doctors_info = ""
    for doc in DOCTORS.values():
        doctors_info += f"\n- {doc['name']} ({doc['specialty']}): ${doc['fee']}/visit, available {', '.join(doc['available'])}"

    system = f"""You are a helpful medical receptionist for {CLINIC['name']}.

Clinic Info:
- Address: {CLINIC['address']}
- Phone: {CLINIC['phone']}
- Hours: {CLINIC['hours']}

Available Doctors:{doctors_info}

Your role:
- Help patients find the right doctor for their symptoms
- Provide general health information (not medical advice)
- Answer questions about appointments, fees, services
- Be empathetic, professional and caring
- Always recommend consulting a doctor for medical concerns
- Respond in the same language as the patient

IMPORTANT: Always remind patients you provide general info only, not medical advice."""

    user_histories[user_id].append({"role": "user", "content": message})
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}, *user_histories[user_id]],
        max_tokens=512,
        temperature=0.7,
    )

    reply = response.choices[0].message.content
    user_histories[user_id].append({"role": "assistant", "content": reply})
    return reply

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Book Appointment", callback_data="book_appointment"),
         InlineKeyboardButton("👨‍⚕️ Our Doctors", callback_data="our_doctors")],
        [InlineKeyboardButton("🏥 Our Services", callback_data="our_services"),
         InlineKeyboardButton("📋 My Appointments", callback_data="my_appointments")],
        [InlineKeyboardButton("🚨 Emergency", callback_data="emergency"),
         InlineKeyboardButton("📍 Location & Hours", callback_data="location")],
        [InlineKeyboardButton("💬 Ask a Question", callback_data="ask_question")],
    ]

    await update.message.reply_text(
        f"🏥 *Welcome to {CLINIC['name']}!*\n"
        f"_{CLINIC['tagline']}_\n\n"
        f"🕐 {CLINIC['hours']}\n"
        f"📞 {CLINIC['phone']}\n\n"
        f"_How can we help you today?_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== DOCTORS ==========
async def show_doctors(update: Update):
    text = "👨‍⚕️ *Our Specialists*\n\n"
    keyboard = []

    for doc_id, doc in DOCTORS.items():
        stars = "⭐" * int(doc['rating'])
        text += f"*{doc['name']}*\n"
        text += f"🏥 {doc['specialty']} | {doc['experience']}\n"
        text += f"💰 ${doc['fee']}/visit | {stars} {doc['rating']}\n"
        text += f"📅 {', '.join(doc['available'])}\n\n"
        keyboard.append([InlineKeyboardButton(
            f"📅 Book with {doc['name'].split()[-1]}", callback_data=f"select_doc_{doc_id}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
    await update.callback_query.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== SERVICES ==========
async def show_services(update: Update):
    text = "🏥 *Our Services*\n\n"
    for service in SERVICES:
        text += f"✅ *{service['name']}*\n"
        text += f"⏱️ {service['duration']} | 💰 ${service['fee']}\n\n"

    text += "_All services performed by certified professionals._"
    keyboard = [
        [InlineKeyboardButton("📅 Book Appointment", callback_data="book_appointment")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_home")],
    ]
    await update.callback_query.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== BOOKING ==========
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📅 *Book an Appointment*\n\nChoose a specialty:"
    specialties = list(set(doc['specialty'] for doc in DOCTORS.values()))
    keyboard = [[InlineKeyboardButton(spec, callback_data=f"spec_{spec}")] for spec in specialties]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])

    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def select_doctor_by_spec(update: Update, specialty: str):
    matching = {did: doc for did, doc in DOCTORS.items() if doc['specialty'] == specialty}
    text = f"👨‍⚕️ *{specialty}*\n\nAvailable doctors:\n\n"
    keyboard = []

    for doc_id, doc in matching.items():
        text += f"*{doc['name']}*\n_{doc['about']}_\n💰 ${doc['fee']}/visit\n\n"
        keyboard.append([InlineKeyboardButton(f"Select {doc['name'].split()[-1]}", callback_data=f"select_doc_{doc_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="book_appointment")])
    await update.callback_query.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_time_slot(update: Update, doc_id: str, user_id: int):
    doc = DOCTORS[doc_id]
    booking_data[user_id] = {"doc_id": doc_id, "doc_name": doc['name'], "fee": doc['fee']}

    keyboard = []
    for slot in doc['slots']:
        keyboard.append([InlineKeyboardButton(
            f"🕐 {slot}", callback_data=f"slot_{doc_id}_{slot.replace(' ', '_').replace(':', '-')}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="our_doctors")])

    await update.callback_query.message.edit_text(
        f"📅 *Select Time Slot*\n\n"
        f"Doctor: *{doc['name']}*\n"
        f"Specialty: {doc['specialty']}\n"
        f"Fee: ${doc['fee']}\n\n"
        f"Available today:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== MY APPOINTMENTS ==========
async def my_appointments(update: Update, user_id: int):
    appointments = user_bookings.get(user_id, [])

    if not appointments:
        text = "📋 *My Appointments*\n\nNo appointments found.\nBook your first appointment!"
        keyboard = [[InlineKeyboardButton("📅 Book Now", callback_data="book_appointment")]]
    else:
        text = "📋 *My Appointments*\n\n"
        for i, apt in enumerate(appointments, 1):
            text += f"{i}. *{apt['doctor']}*\n"
            text += f"   🕐 {apt['time']} | 💰 ${apt['fee']}\n"
            text += f"   🔖 ID: `{apt['id']}`\n\n"
        keyboard = [[InlineKeyboardButton("📅 Book Another", callback_data="book_appointment")]]

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
    await update.callback_query.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== CALLBACK ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "book_appointment":
        await start_booking(update, context)

    elif data.startswith("spec_"):
        specialty = data.replace("spec_", "")
        await select_doctor_by_spec(update, specialty)

    elif data == "our_doctors":
        await show_doctors(update)

    elif data == "our_services":
        await show_services(update)

    elif data.startswith("select_doc_"):
        doc_id = data.replace("select_doc_", "")
        await select_time_slot(update, doc_id, user_id)

    elif data.startswith("slot_"):
        parts = data.split("_", 2)
        doc_id = parts[1]
        time = parts[2].replace("_", " ").replace("-", ":")
        doc = DOCTORS[doc_id]

        apt_id = f"APT-{random.randint(10000, 99999)}"
        appointment = {
            "id": apt_id,
            "doctor": doc['name'],
            "specialty": doc['specialty'],
            "time": time,
            "fee": doc['fee']
        }

        if user_id not in user_bookings:
            user_bookings[user_id] = []
        user_bookings[user_id].append(appointment)

        text = f"✅ *Appointment Confirmed!*\n\n"
        text += f"🔖 Booking ID: `{apt_id}`\n"
        text += f"👨‍⚕️ Doctor: *{doc['name']}*\n"
        text += f"🏥 Specialty: {doc['specialty']}\n"
        text += f"🕐 Time: {time} Today\n"
        text += f"💰 Fee: ${doc['fee']}\n"
        text += f"📍 {CLINIC['address']}\n\n"
        text += f"📧 Confirmation sent to your email\n"
        text += f"📞 Questions: {CLINIC['phone']}\n\n"
        text += f"_Please arrive 10 minutes early. Bring your ID._"

        keyboard = [
            [InlineKeyboardButton("📋 My Appointments", callback_data="my_appointments")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back_home")],
        ]
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "my_appointments":
        await my_appointments(update, user_id)

    elif data == "emergency":
        text = f"🚨 *Emergency Information*\n\n"
        text += f"🆘 *For life-threatening emergencies:*\n"
        text += f"Call *911* immediately!\n\n"
        text += f"🏥 *Our Emergency Line:*\n"
        text += f"{CLINIC['emergency']}\n\n"
        text += f"📍 *Nearest ER:*\n"
        text += f"New York General Hospital\n"
        text += f"789 Emergency Blvd, NY\n\n"
        text += f"⚠️ *Warning Signs:*\n"
        text += f"• Chest pain or pressure\n"
        text += f"• Difficulty breathing\n"
        text += f"• Sudden severe headache\n"
        text += f"• Signs of stroke (FAST)\n\n"
        text += f"_When in doubt, call 911!_"

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "location":
        text = f"📍 *Location & Hours*\n\n"
        text += f"🏥 *{CLINIC['name']}*\n"
        text += f"{CLINIC['address']}\n\n"
        text += f"🕐 *Hours:*\n{CLINIC['hours']}\n\n"
        text += f"📞 {CLINIC['phone']}\n"
        text += f"📧 {CLINIC['email']}\n\n"
        text += f"🅿️ Free parking | ♿ Accessible"

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "ask_question":
        await query.message.reply_text(
            "💬 *Ask Us Anything!*\n\n"
            "Type your question — I can help with:\n"
            "• Finding the right doctor\n"
            "• Appointment information\n"
            "• General health questions\n"
            "• Clinic services & fees\n\n"
            "_Just type below_ 👇",
            parse_mode="Markdown"
        )

    elif data == "back_home":
        keyboard = [
            [InlineKeyboardButton("📅 Book Appointment", callback_data="book_appointment"),
             InlineKeyboardButton("👨‍⚕️ Our Doctors", callback_data="our_doctors")],
            [InlineKeyboardButton("🏥 Our Services", callback_data="our_services"),
             InlineKeyboardButton("📋 My Appointments", callback_data="my_appointments")],
            [InlineKeyboardButton("🚨 Emergency", callback_data="emergency"),
             InlineKeyboardButton("📍 Location & Hours", callback_data="location")],
            [InlineKeyboardButton("💬 Ask a Question", callback_data="ask_question")],
        ]
        await query.message.edit_text(
            f"🏥 *{CLINIC['name']} — Main Menu*\n\n_How can we help you?_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = await get_ai_response(user_id, message)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again!")

# ========== MAIN ==========
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🏥 Clinic Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
