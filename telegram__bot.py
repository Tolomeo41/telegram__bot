import sqlite3
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import nest_asyncio, asyncio

DB_FILE = 'abbonamenti.db'
BOT_TOKEN = '8094964186:AAGnHUJydHxqy7XkgGCh35sgxTlqDSxqHIs'
AUTHORIZED_USERS = [435544119]  # Inserisci qui gli ID degli admin

# ---------- DB ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abbonamenti (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            scadenza TEXT,
            nome TEXT,
            cognome TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ---------- COMANDI ----------
async def registrami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Non sei autorizzato a usare questo comando.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("Formato corretto: /registrami AAAA-MM-GG Nome Cognome")
        return

    scadenza, nome, cognome = context.args[0], context.args[1], ' '.join(context.args[2:])
    username = update.effective_user.username or "NessunUsername"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO abbonamenti (user_id, username, scadenza, nome, cognome)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            scadenza=excluded.scadenza,
            nome=excluded.nome,
            cognome=excluded.cognome
    ''', (user_id, username, scadenza, nome, cognome))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Registrato: {nome} {cognome} - Scadenza: {scadenza}")

async def scadenza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.callback_query.from_user if hasattr(update, 'callback_query') and update.callback_query else update.effective_user
    user_id = user.id

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT scadenza FROM abbonamenti WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    text = f"📆 La tua scadenza è: {row[0]}" if row else "❌ Nessuna scadenza trovata. Usa /registrami AAAA-MM-GG Nome Cognome"
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def lista_iscritti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Non sei autorizzato a vedere questa lista.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, scadenza, nome, cognome FROM abbonamenti ORDER BY scadenza ASC')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 Nessun utente registrato.")
        return

    elenco = [
        f"👤 {n} {c} (@{u} - `{uid}`): {s}" if u != "NessunUsername" else f"👤 {n} {c} (`{uid}`): {s}"
        for uid, u, s, n, c in rows
    ]
    await update.message.reply_text("📋 Lista iscritti:\n\n" + "\n".join(elenco), parse_mode="Markdown")

# ---------- MENU ----------
def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Registrami (solo admin)", callback_data="registrami")],
        [InlineKeyboardButton("⏳ Scadenza abbonamento", callback_data="scadenza_abbonamento")],
        [InlineKeyboardButton("📄 Lista iscritti (solo admin)", callback_data="lista_iscritti")],
        [InlineKeyboardButton("📹 Video esercizi", callback_data="video_esercizi")],
        [InlineKeyboardButton("🧠 Consigli integrazione", callback_data="consigli_integrazione")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    benvenuto = (
        f"👋 Ciao *{update.effective_user.first_name}*! Benvenutə nel Fitness Bot 💪\n\n"
        "Puoi fare tutte queste azioni:\n"
        "• `/help` – Apri il menu interattivo\n"
        "• `/registrami AAAA-MM-GG Nome Cognome` – Registra o aggiorna la tua scadenza (solo admin)\n"
        "• `/scadenza` – Vedi la tua data di scadenza\n"
        "• `/lista_iscritti` – Lista completa degli iscritti (solo admin)\n\n"
        "Se vuoi video, consigli o controllare la scadenza, usa i pulsanti qui sotto 👇"
    )

    await update.message.reply_text(
        benvenuto,
        reply_markup=menu_keyboard(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Seleziona un'opzione:", reply_markup=menu_keyboard())

# ---------- BOTTONI ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "registrami":
        if user_id in AUTHORIZED_USERS:
            await query.edit_message_text("✍️ Per registrarti usa il comando:\n`/registrami AAAA-MM-GG Nome Cognome`", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Solo gli admin possono registrare utenti.")
    elif query.data == "scadenza_abbonamento":
        await scadenza(update, context)
    elif query.data == "lista_iscritti":
        if user_id in AUTHORIZED_USERS:
            await lista_iscritti(update, context)
        else:
            await query.edit_message_text("❌ Solo gli admin possono vedere la lista iscritti.")
    elif query.data == "video_esercizi":
        await query.edit_message_text(
            "Scegli un gruppo muscolare:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🦵 Gambe", url="https://www.youtube.com/watch?v=vid1")],
                [InlineKeyboardButton("💪 Braccia", url="https://www.youtube.com/watch?v=vid2")],
                [InlineKeyboardButton("🧱 Petto",  url="https://www.youtube.com/watch?v=vid3")],
                [InlineKeyboardButton("🦅 Schiena",url="https://www.youtube.com/watch?v=vid4")],
                [InlineKeyboardButton("🎯 Spalle", url="https://www.youtube.com/watch?v=vid5")],
                [InlineKeyboardButton("🔥 Addominali", url="https://www.youtube.com/watch?v=vid6")]
            ])
        )
    elif query.data == "consigli_integrazione":
        await query.edit_message_text("🧠 Consigli:\n- Proteine al mattino\n- Omega-3 dopo pranzo\n- Magnesio la sera")

# ---------- JOBS ----------
async def notifica_scadenze_job(context: ContextTypes.DEFAULT_TYPE):
    oggi, fra_3 = datetime.now().date(), datetime.now().date() + timedelta(days=3)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, nome, cognome, scadenza FROM abbonamenti')
    for uid, nome, cognome, scad in cursor.fetchall():
        try:
            data = datetime.strptime(scad, '%Y-%m-%d').date()
            if oggi <= data <= fra_3:
                await context.bot.send_message(uid, f"⚠️ {nome} {cognome}, il tuo abbonamento scade il {scad}.")
        except Exception as e:
            print(f"Errore notifica {uid}: {e}")
    conn.close()

async def reminder_peso_check(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, nome, cognome FROM abbonamenti')
    for uid, n, c in cursor.fetchall():
        try:
            await context.bot.send_message(uid, f"📅 {n} {c}, ricorda peso + check settimanale!")
        except: pass
    conn.close()

async def reminder_foto_bisettimanale(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, nome, cognome FROM abbonamenti')
    for uid, n, c in cursor.fetchall():
        try:
            await context.bot.send_message(
                uid,
                f"📸 {n} {c}, questa settimana invia:\n- peso\n- check\n- foto 4 lati (fronte, retro, dx, sx)."
            )
        except: pass
    conn.close()

# ---------- MAIN ----------
async def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('registrami', registrami))
    app.add_handler(CommandHandler('scadenza', scadenza))
    app.add_handler(CommandHandler('lista_iscritti', lista_iscritti))
    app.add_handler(CallbackQueryHandler(button_handler))

    jq = app.job_queue
    jq.run_daily(notifica_scadenze_job, time=time(9, 0, 0))
    jq.run_daily(reminder_peso_check, time=time(9, 0, 0), days=(4,))   # venerdì
    jq.run_daily(reminder_foto_bisettimanale, time=time(9, 0, 0), days=(6,)) # domenica

    print("🤖 Il bot è avviato e funzionante!")
    await app.run_polling()

# ---------- START ----------
if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())
