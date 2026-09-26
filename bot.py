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
def load_db(): return load_j("database.json", {"qris_statis": os.getenv("QRIS_STATIS",""), "produk": {}})
def save_db(d): save_j("database.json", d)

NAMA, HARGA, SET_QRIS, NOMINAL_BEBAS = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    banned = load_j("banned.json", [])
    if uid in banned: await update.message.reply_text("🚫 AKUN LU DI-BANNED."); return
    users = load_j("users.json", [])
    if uid not in users: users.append(uid); save_j("users.json", users)
    db = load_db()
    text = f"✨ *{STORE_NAME}* ✨\n━━━━━━━━━━━━━━━\n🛍️ PILIH PRODUK / NOMINAL BEBAS, BAYAR QRIS, OTOMATIS TERKIRIM."
    kb = [[InlineKeyboardButton(f"{v['nama'].upper()} - RP{v['harga']:,}", callback_data=f"buy_{k}")] for k,v in db["produk"].items()]
    kb.append([InlineKeyboardButton("💰 NOMINAL BEBAS (MIN 1K)", callback_data="bebas")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

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

async def bebas_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    await q.message.reply_text("KIRIM NOMINAL (MIN RP1.000):", parse_mode='Markdown'); return NOMINAL_BEBAS
async def bebas_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: nominal=int(update.message.text.replace(".",""))
    except: await update.message.reply_text("HARUS ANGKA!"); return NOMINAL_BEBAS
    if nominal < 1000: await update.message.reply_text("🚫 MINIMAL RP1.000!"); return NOMINAL_BEBAS
    db=load_db(); total=nominal+random.randint(11,99)
    context.user_data.update({'tagihan':total,'produk':f"CUSTOM RP{nominal:,}",'pid':'custom'})
    qrcode.make(f"{db['qris_statis']}|{total}").save("/tmp/qris.png")
    await update.message.reply_photo(open("/tmp/qris.png","rb"), caption=f"🧾 *INVOICE CUSTOM - {STORE_NAME}*\n💰 *RP{total:,}*", parse_mode='Markdown')
    return ConversationHandler.END

async def auto_cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; tagihan=context.user_data.get('tagihan')
    if not tagihan: await update.message.reply_text("KLIK /START DULU."); return
    pid=context.user_data.get('pid','custom'); stok=load_j("stok.json", {})
    kode=f"AUTO-{random.randint(1000,9999)}"
    if pid in stok and stok[pid]: kode=stok[pid].pop(0); save_j("stok.json", stok)
    trx=load_j("trx.json", []); trx.append({"user":uid,"produk":context.user_data.get('produk'),"total":tagihan,"kode":kode})
    save_j("trx.json", trx); context.user_data.clear()
    await update.message.reply_text(f"✅ *PEMBAYARAN DITERIMA - {STORE_NAME}*\n📦 {trx[-1]['produk'].upper()}\n🔑 KODE LU:\n`{kode}`", parse_mode='Markdown')

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
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(del_exec, pattern="^del_p"))
    app.add_handler(CallbackQueryHandler(del_list, pattern="^del_list$"))
    app.add_handler(CallbackQueryHandler(list_prod, pattern="^list_prod$"))
    app.add_handler(CallbackQueryHandler(list_ban, pattern="^list_ban$"))
    app.add_handler(MessageHandler(filters.PHOTO, auto_cek))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(add_start, pattern="^add_prod$")], states={NAMA:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_nama)], HARGA:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_harga)]}, fallbacks=[]))
    app.add_handler(ConversationHandler(entry_points=[CommandHandler("set_qris", set_qris_start)], states={SET_QRIS:[MessageHandler(filters.TEXT & ~filters.COMMAND, set_qris_save)]}, fallbacks=[]))
    app.add_handler(ConversationHandler(entry_points=[CallbackQueryHandler(bebas_start, pattern="^bebas$")], states={NOMINAL_BEBAS:[MessageHandler(filters.TEXT & ~filters.COMMAND, bebas_exec)]}, fallbacks=[]))
    app.run_polling()
if __name__=="__main__": main()
