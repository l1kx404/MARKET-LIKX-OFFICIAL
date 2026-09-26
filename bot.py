import os, json, random, qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
STORE_NAME = "MARKET LIKX OFFICIAL"

def load_j(f, d):
    try: return json.load(open(f))
    except: return d
def save_j(f, d): open(f,"w").write(json.dumps(d, indent=2))
def load_db(): return load_j("database.json", {"qris_statis": os.getenv("QRIS_STATIS",""), "produk": {}, "channel_info": ""})
def save_db(d): save_j("database.json", d)

NAMA, HARGA, SET_QRIS = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    banned = load_j("banned.json", [])
    if uid in banned: await update.message.reply_text("🚫 AKUN LU DI-BANNED."); return
    users = load_j("users.json", [])
    if uid not in users: users.append(uid); save_j("users.json", users)
    db = load_db()
    text = f"✨ *{STORE_NAME}* ✨\n━━━━━━━━━━━━━━━\n🛍️ PILIH PRODUK, BAYAR QRIS."
    kb = [[InlineKeyboardButton(f"{v['nama'].upper()} - RP{v['harga']:,}", callback_data=f"buy_{k}")] for k,v in db["produk"].items()]
    kb.append([InlineKeyboardButton("📢 CHANNEL INFO", callback_data="channel_info")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def channel_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    db = load_db()
    info = db.get("channel_info", "")
    if not info: info = "Belum di-set admin. Hubungi admin untuk info channel."
    await q.message.reply_text(f"📢 *CHANNEL INFO - {STORE_NAME}*\n\n{info}", parse_mode='Markdown')

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    teks = update.message.text.split(" ", 1)
    if len(teks) < 2 or not teks[1].strip():
        await update.message.reply_text("Pakai: `/set_channel https://t.me/channel lu | info lain`", parse_mode='Markdown')
        return
    db = load_db(); db["channel_info"] = teks[1].strip(); save_db(db)
    await update.message.reply_text("✅ CHANNEL INFO UPDATE!")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    db=load_db(); pid=q.data.split("_",1)[1]; p=db["produk"][pid]
    stok = load_j("stok.json", {})
    if pid in stok and not stok[pid]:
        await q.message.reply_text("🚫 STOK HABIS!"); return
    unik=random.randint(11,99); total=p['harga']+unik
    context.user_data.update({'tagihan':total,'produk':p['nama'],'pid':pid})
    qrcode.make(f"{db['qris_statis']}|{total}").save("/tmp/qris.png")
    await q.message.reply_photo(open("/tmp/qris.png","rb"), caption=f"🧾 *INVOICE - {STORE_NAME}*\n📦 {p['nama'].upper()}\n💰 *RP{total:,}*\n\nKIRIM FOTO BUKTI.", parse_mode='Markdown')

async def foto_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tagihan = context.user_data.get('tagihan')
    if not tagihan:
        await update.message.reply_text("KLIK /start DULU."); return
    pending = load_j("pending.json", [])
    pending.append({"user": uid,"produk": context.user_data.get('produk'),"pid": context.user_data.get('pid','custom'),"total": tagihan,"file_id": update.message.photo[-1].file_id})
    save_j("pending.json", pending)
    idx = len(pending)-1
    await update.message.reply_text("MOHON TUNGGU!!!\nADMIN AKAN SEGARA MENGECEK BUKTI TRANSAKSI ANDA ⚠️")
    kb = [[InlineKeyboardButton("✅ ACC", callback_data=f"acc_{idx}"),InlineKeyboardButton("❌ TOLAK", callback_data=f"tolak_{idx}")]]
    await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=f"🧾 PENDING\nUser: {uid}\nProduk: {context.user_data.get('produk')}\nTotal: RP{tagihan:,}", reply_markup=InlineKeyboardMarkup(kb))
    context.user_data.clear()

async def acc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if update.effective_user.id!= ADMIN_ID: return
    action, idx = q.data.split("_"); idx = int(idx)
    pending = load_j("pending.json", [])
    if idx >= len(pending): return
    data = pending[idx]
    if action == "acc":
        stok = load_j("stok.json", {}); pid = data['pid']; kode = f"AUTO-{random.randint(1000,9999)}"
        if pid in stok and stok[pid]: kode = stok[pid].pop(0); save_j("stok.json", stok)
        trx = load_j("trx.json", []); trx.append(data); save_j("trx.json", trx)
        await context.bot.send_message(data['user'], f"✅ PEMBAYARAN DI-ACC ADMIN\n📦 {data['produk'].upper()}\n🔑 KODE LU:\n`{kode}`", parse_mode='Markdown')
        await q.message.reply_text("✅ Udah dikirim ke user.")
    else:
        await context.bot.send_message(data['user'], "❌ BUKTI DITOLAK.\nFoto ngasal / nominal nggak sesuai mutasi.\nBayar dulu yang bener baru kirim bukti lagi.")
        await q.message.reply_text("❌ Udah ditolak.")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    kb=[[InlineKeyboardButton("➕ TAMBAH PRODUK", callback_data="add_prod")],[InlineKeyboardButton("🗑️ HAPUS PRODUK", callback_data="del_list")],[InlineKeyboardButton("📦 LIHAT PRODUK", callback_data="list_prod")],[InlineKeyboardButton("🚫 LIST BANNED", callback_data="list_ban")]]
    await update.message.reply_text(f"⚙️ *{STORE_NAME} - PANEL ADMIN*", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); await q.message.reply_text("KIRIM *NAMA PRODUK*:", parse_mode='Markdown'); return NAMA
async def add_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nama_baru']=update.message.text; await update.message.reply_text("KIRIM *HARGA*:", parse_mode='Markdown'); return HARGA
async def add_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db=load_db(); pid=f"p{random.randint(100,999)}"; db['produk'][pid]={"nama":context.user_data['nama_baru'],"harga":int(update.message.text)}; save_db(db)
    await update.message.reply_text(f"✅ TERSIMPAN! ID: `{pid}`", parse_mode='Markdown'); return ConversationHandler.END
async def list_prod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); db=load_db(); stok=load_j("stok.json", {})
    txt="\n".join([f"- {v['nama'].upper()} : RP{v['harga']:,} | STOK:{len(stok.get(k,[]))} | {k}" for k,v in db["produk"].items()]) or "KOSONG"
    await q.message.reply_text(f"📦 *{STORE_NAME}*\n{txt}", parse_mode='Markdown')
async def del_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); db=load_db()
    kb=[[InlineKeyboardButton(f"🗑️ {v['nama'].upper()}", callback_data=f"del_{k}")] for k,v in db["produk"].items()]
    await q.message.reply_text("PILIH:", reply_markup=InlineKeyboardMarkup(kb))
async def del_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); db=load_db(); pid=q.data.split("_",1)[1]
    if pid in db["produk"]: del db["produk"][pid]; save_db(db)
    await q.message.reply_text("✅ DIHAPUS!")
async def list_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); await q.message.reply_text(f"🚫 {load_j('banned.json',[])}")
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    b=load_j("banned.json",[]); b.append(int(context.args[0])); save_j("banned.json",b); await update.message.reply_text("✅ BANNED.")
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    b=load_j("banned.json",[]); b.remove(int(context.args[0])); save_j("banned.json",b); await update.message.reply_text("✅ UNBANNED.")
async def set_qris_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    await update.message.reply_text("KIRIM STRING QRIS:"); return SET_QRIS
async def set_qris_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db=load_db(); db["qris_statis"]=update.message.text.strip(); save_db(db)
    await update.message.reply_text("✅ QRIS UPDATE!"); return ConversationHandler.END
async def addstok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    try: pid=context.args[0]
    except: await update.message.reply_text("PAKAI: `/addstok p123`", parse_mode='Markdown'); return
    isi=update.message.text.split("\n")[1:]; s=load_j("stok.json", {}); s[pid]=s.get(pid,[])+[x.strip() for x in isi if x.strip()]; save_j("stok.json", s)
    await update.message.reply_text(f"✅ {len(isi)} KODE MASUK. TOTAL: {len(s[pid])}")
async def omset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    trx=load_j("trx.json", []); total=sum(x['total'] for x in trx)
    await update.message.reply_text(f"💰 *{STORE_NAME} - OMSET*\n📊 TRANSAKSI: {len(trx)}\n💵 TOTAL: RP{total:,}", parse_mode='Markdown')
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    pesan=" ".join(context.args); users=load_j("users.json", []); ok=0
    for uid in users:
        try: await context.bot.send_message(uid, f"📢 *{STORE_NAME}*\n\n{pesan}", parse_mode='Markdown'); ok+=1
        except: pass
    await update.message.reply_text(f"✅ TERKIRIM KE {ok} USER.")

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("omset", omset))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("addstok", addstok))
    app.add_handler(CommandHandler("set_channel", set_channel))
    app.add_handler(CallbackQueryHandler(channel_info, pattern="^channel_info$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(del_exec, pattern="^del_p"))
    app.add_handler(CallbackQueryHandler(del_list, pattern="^del
