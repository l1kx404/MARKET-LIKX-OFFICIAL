import os, json, qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"products": {}, "qris": "BELUM DISET", "banned": [], "omset": 0, "users": []}
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {"products": {}, "qris": "BELUM DISET", "banned": [], "omset": 0, "users": []}

def save_data(d):
    with open(DATA_FILE, "w") as f: json.dump(d, f)

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    uid = u.effective_user.id
    if uid in d["banned"]: return
    if uid not in d["users"]:
        d["users"].append(uid); save_data(d)
    kb = [[InlineKeyboardButton("💰 NOMINAL BEBAS (MIN 1K)", callback_data="bebas")]]
    for pid, p in d["products"].items():
        kb.append([InlineKeyboardButton(f"{p['nama']} - Rp{p['harga']:,} (Stok:{len(p['codes'])})", callback_data=f"buy_{pid}")])
    await u.message.reply_text("✨ MARKET LIKX OFFICIAL ✨\n🛍️ PILIH PRODUK, BAYAR QRIS, OTOMATIS TERKIRIM.",
        reply_markup=InlineKeyboardMarkup(kb))

async def panel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id!= ADMIN_ID: return
    kb = [
        [InlineKeyboardButton("➕ TAMBAH PRODUK", callback_data="add_prod")],
        [InlineKeyboardButton("🗑️ HAPUS PRODUK", callback_data="del_prod")],
        [InlineKeyboardButton("📦 LIHAT PRODUK", callback_data="list_prod")],
        [InlineKeyboardButton("🚫 LIST BANNED", callback_data="list_ban")],
    ]
    await u.message.reply_text("⚙️ PANEL ADMIN", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    d = load_data()
    data = q.data
    try:
        if data == "bebas":
            c.user_data["mode"] = "input_nominal"
            await q.message.reply_text("Masukin nominal (min 1000):\nContoh: 15000")
        elif data.startswith("buy_"):
            pid = data[4:]
            p = d["products"].get(pid)
            if not p or not p["codes"]:
                await q.message.reply_text("Stok habis."); return
            c.user_data["mode"] = "bayar"
            c.user_data["pid"] = pid
            c.user_data["harga"] = p["harga"]
            qr = qrcode.make(d["qris"]); qr.save("qris.png")
            await q.message.reply_photo(open("qris.png","rb"), caption=f"Bayar Rp{p['harga']:,}\nKlik ✅ SUDAH BAYAR",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ SUDAH BAYAR", callback_data="paid")]]))
        elif data == "paid" or data == "paid_bebas":
            pid = c.user_data.get("pid")
            harga = c.user_data.get("harga", 0)
            if data == "paid_bebas":
                d["omset"] += harga; save_data(d)
                await q.message.reply_text(f"✅ Terima kasih! Pembayaran Rp{harga:,} diterima.\nAdmin akan cek manual.")
            else:
                if not pid or pid not in d["products"]:
                    await q.message.reply_text("Sesi expired, /start lagi"); return
                p = d["products"][pid]
                if not p["codes"]:
                    await q.message.reply_text("Stok habis."); return
                kode = p["codes"].pop(0)
                d["omset"] += harga; save_data(d)
                await q.message.reply_text(f"✅ PEMBAYARAN DITERIMA\nKode lu:\n`{kode}`", parse_mode="Markdown")
            c.user_data.clear()
        elif data == "add_prod":
            c.user_data["mode"] = "add_prod"
            await q.message.reply_text("Format:\nNAMA | HARGA\nContoh:\nNetflix 1 Bulan | 15000")
        elif data == "del_prod":
            kb = [[InlineKeyboardButton(p["nama"], callback_data=f"del_{pid}")] for pid,p in d["products"].items()]
            await q.message.reply_text("Pilih hapus:", reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        elif data.startswith("del_"):
            pid = data[4:]
            if pid in d["products"]: del d["products"][pid]; save_data(d)
            await q.message.reply_text("Dihapus.")
        elif data == "list_prod":
            t = "\n".join([f"{pid}: {p['nama']} Rp{p['harga']:,} stok:{len(p['codes'])}" for pid,p in d["products"].items()]) or "Kosong"
            await q.message.reply_text(t)
        elif data == "list_ban":
            await q.message.reply_text("Banned: "+str(d["banned"]))
    except Exception as e:
        await q.message.reply_text(f"Error: {e}")

async def msg_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    mode = c.user_data.get("mode")
    txt = u.message.text or ""
    d = load_data()
    if mode == "input_nominal":
        if not txt.isdigit():
            await u.message.reply_text("Angka aja."); return
        n = int(txt)
        if n < 1000:
            await u.message.reply_text("Min 1k"); return
        c.user_data["mode"]="bayar"; c.user_data["harga"]=n; c.user_data["pid"]="NOMINAL_BEBAS"
        qr = qrcode.make(d["qris"]); qr.save("qris.png")
        await u.message.reply_photo(open("qris.png","rb"), caption=f"Bayar Rp{n:,}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ SUDAH BAYAR", callback_data="paid_bebas")]]))
    elif mode == "add_prod" and u.effective_user.id==ADMIN_ID:
        if "|" not in txt:
            await u.message.reply_text("Format salah. Contoh: Netflix | 15000"); return
        nama,harga = [x.strip() for x in txt.split("|",1)]
        pid = f"p{len(d['products'])+1}"
        d["products"][pid]={"nama":nama,"harga":int(harga),"codes":[]}
        save_data(d); c.user_data.clear()
        await u.message.reply_text(f"OK {nama} ID:{pid}\nIsi stok: /addstok {pid}")

async def set_qris(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id!=ADMIN_ID: return
    d=load_data(); d["qris"]=" ".join(c.args) if c.args else "BELUM DISET"; save_data(d)
    await u.message.reply_text("QRIS updated.")

async def addstok(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id!=ADMIN_ID or not c.args: return
    c.user_data["addstok_pid"]=c.args[0]
    c.user_data["mode"]="addstok"
    await u.message.reply_text(f"Kirim kode untuk {c.args[0]}, 1 baris 1 kode.")

# handle addstok text
async def msg_wrapper(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if c.user_data.get("mode")=="addstok":
        d=load_data(); pid=c.user_data["addstok_pid"]
        codes=[x.strip() for x in u.message.text.split("\n") if x.strip()]
        if pid in d["products"]:
            d["products"][pid]["codes"].extend(codes); save_data(d)
            await u.message.reply_text(f"Stok nambah {len(codes)}")
        c.user_data.clear(); return
    await msg_handler(u,c)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("panel", panel))
app.add_handler(CommandHandler("set_qris", set_qris))
app.add_handler(CommandHandler("addstok", addstok))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_wrapper))
print("Bot jalan...")
app.run_polling()
