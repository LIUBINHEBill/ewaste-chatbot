import os, random, time, streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from utils.retriever import search

# ========== OpenAI & 环境 ==========
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"             # 若无权限可换 "gpt-3.5-turbo"

# ========== 页面 ==========
st.set_page_config(page_title="E-waste Tutor", page_icon="♻", layout="wide")
st.markdown("""
<style>
div.stChatMessage:nth-child(odd)>div[data-testid="stMarkdownContainer"]{
 background:#DCF8C6;border-radius:8px;padding:8px 14px;}
div.stChatMessage:nth-child(even)>div[data-testid="stMarkdownContainer"]{
 background:#F1F0F0;border-radius:8px;padding:8px 14px;}
section.main>div{overflow-y:auto;}
</style>
""", unsafe_allow_html=True)
st.title("♻️ Electronic Waste & Circular Economy Chatbot")
st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)

# ========== Session State ==========
def ss_init(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

ss_init("messages",      [])
ss_init("stage",         1)      # 1=Understand, 2=Control, 3=Improve
ss_init("awaiting_quiz", False)
ss_init("quiz_answer",   "")
ss_init("quiz_expl",     "")
ss_init("just_switched", False)
ss_init("plan_sent",     False)  # Improve 阶段是否已自动推送过计划

# ========== 题库（5 道） ==========
quiz_bank = [
    ("Global formal e-waste recycling rate in 2022 was roughly…\n"
     "A) 10 %  B) 22 %  C) 35 %", "B",
     "UN Global E-Waste Monitor 2024 reports a 22.3 % formal collection rate."),
    ("Which metal is commonly recovered from printed circuit boards?\n"
     "A) Platinum  B) Gold  C) Lithium", "B",
     "Gold is economically viable to recover from PCBs."),
    ("Which hazardous chemical can leach from improperly landfilled e-waste?\n"
     "A) Mercury  B) Sodium  C) Nitrogen", "A",
     "Mercury and lead are common toxics in discarded electronics."),
    ("Extended Producer Responsibility (EPR) means manufacturers must…\n"
     "A) Pay for end-of-life collection  B) Provide lifetime warranty  C) Ban plastics", "A",
     "EPR shifts financial/organizational responsibility of e-waste to producers."),
    ("Fairphone’s modular design mainly aims to…\n"
     "A) Increase device thickness  B) Facilitate user repair  C) Improve water-proofing", "B",
     "Modules let users replace parts easily; iFixit scores are 10/10.")
]

# Improve 阶段：5 套行动计划
plans_bank = [
    ("### 3-Step Action Plan\n"
     "1. **Declutter & Drop-off** – Find a certified e-waste collection point this week.\n"
     "2. **Repair First** – Replace batteries/screens before buying new; use iFixit guides.\n"
     "3. **Buy Circular** – Prefer devices with take-back programmes like Fairphone.\n\n"
     "**Case:** Keeping Fairphone 4 for 5 yrs cuts lifecycle CO₂ e by 31 % (Fraunhofer IZM 2022)."),

    ("### 3-Step Action Plan\n"
     "1. **Data-wipe & Donate** – Secure-erase old phones and donate to Closing the Loop.\n"
     "2. **Universal Chargers** – Switch to USB-C multi-port bricks to reduce redundant chargers.\n"
     "3. **Advocate** – Email campus facilities to install e-waste drop-bins.\n\n"
     "**Case:** Dell’s Asset Recovery Service recycled & reused 226 kt electronics in 2023."),

    ("### 3-Step Action Plan\n"
     "1. **Inventory Gadgets** – List unused electronics; schedule quarterly clear-outs.\n"
     "2. **Modular Accessories** – Choose replaceable-cell power banks instead of sealed ones.\n"
     "3. **Lease, Don’t Own** – Opt for IT leasing contracts with take-back clauses.\n\n"
     "**Case:** Vodafone Germany’s phone-leasing model recovers 90 % devices after 24 months."),

    ("### 3-Step Action Plan\n"
     "1. **Share & Swap** – Organise an ‘old gadget swap day’ in your dorm or office.\n"
     "2. **Extend Warranties** – Buy extended manufacturer repair plans instead of new devices.\n"
     "3. **Track Footprint** – Use apps like Carbonalyser to see device-in-use energy.\n\n"
     "**Case:** Orange ‘Re’ programme collected 2 M phones for refurbishment (2022)."),

    ("### 3-Step Action Plan\n"
     "1. **Refurb First** – When upgrading, consider certified refurbished over brand-new.\n"
     "2. **Mod Upgrade** – Upgrade only the camera module instead of whole phone where possible.\n"
     "3. **Close the Loop** – Return spent Li-ion batteries to OEM recycling streams.\n\n"
     "**Case:** Apple recovered 2 400 kg gold from recycled iPhones in 2021.")
]

# ---------- 让题目/计划不重复 ----------
ss_init("remaining_quizzes", quiz_bank.copy())
ss_init("remaining_plans",   plans_bank.copy())

def launch_quiz():
    # 若全部出完则重置
    if not st.session_state.remaining_quizzes:
        st.session_state.remaining_quizzes = quiz_bank.copy()
    q, ans, expl = random.choice(st.session_state.remaining_quizzes)
    st.session_state.remaining_quizzes.remove((q, ans, expl))

    st.session_state.awaiting_quiz = True
    st.session_state.quiz_answer   = ans
    st.session_state.quiz_expl     = expl
    quiz_msg = f"📝 **Quiz time!**\n\n{q}\n\n*Reply with A, B, or C.*"
    with st.chat_message("assistant"): st.markdown(quiz_msg)
    st.session_state.messages.append({"role": "assistant", "content": quiz_msg})

def send_plan():
    if not st.session_state.remaining_plans:
        st.session_state.remaining_plans = plans_bank.copy()
    plan_msg = random.choice(st.session_state.remaining_plans)
    st.session_state.remaining_plans.remove(plan_msg)

    with st.chat_message("assistant"): st.markdown(plan_msg)
    st.session_state.messages.append({"role":"assistant","content":plan_msg})

# ========== 侧栏 ==========
stages = {1: "Understand", 2: "Control", 3: "Improve"}
st.sidebar.header("ℹ️  About")
st.sidebar.write(
    "Chat with me to learn about electronic waste, recycling, and circular-economy solutions. "
    "Answers combine GPT-4o-mini intelligence with a curated knowledge base."
)
st.sidebar.subheader("🎯 Learning Stage")
st.sidebar.write(f"Current stage：**{stages[st.session_state.stage]}**")
if st.session_state.stage < 3:
    if st.sidebar.button("➡️  Next Stage"):
        st.session_state.stage += 1
        st.session_state.just_switched = True
        st.rerun()

# ========== 历史对话 ==========
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 若刚切阶段
if st.session_state.just_switched:
    st.session_state.just_switched = False
    tip = f"✅ Already came into **{stages[st.session_state.stage]}** stage！"
    with st.chat_message("assistant"): st.markdown(tip)
    st.session_state.messages.append({"role": "assistant", "content": tip})
    if st.session_state.stage == 2:
        launch_quiz()
    if st.session_state.stage == 3 and not st.session_state.plan_sent:
        send_plan()
        st.session_state.plan_sent = True

# ========== 输入框 ==========
user_msg = st.chat_input("Type your message…")

# ---------- 答题模式 ----------
if user_msg and st.session_state.stage == 2 and st.session_state.awaiting_quiz:
    choice = user_msg.strip().upper()[:1]
    if choice == st.session_state.quiz_answer:
        feedback = f"✅ Correct! {st.session_state.quiz_expl}"
    else:
        feedback = f"❌ Not quite. {st.session_state.quiz_expl}"
    with st.chat_message("user"):      st.markdown(user_msg)
    with st.chat_message("assistant"): st.markdown(feedback)
    st.session_state.messages.extend([
        {"role": "user",      "content": user_msg},
        {"role": "assistant", "content": feedback},
    ])
    st.session_state.awaiting_quiz = False
    user_msg = None

# ---------- Control: 用户主动要求新题 ----------
if user_msg and st.session_state.stage == 2 and user_msg.strip().lower() == "quiz":
    with st.chat_message("user"): st.markdown(user_msg)
    st.session_state.messages.append({"role":"user","content":user_msg})
    launch_quiz()
    user_msg = None

# ---------- Improve: 用户主动要新计划 ----------
if user_msg and st.session_state.stage == 3 and user_msg.strip().lower() in {"plan", "行动"}:
    with st.chat_message("user"): st.markdown(user_msg)
    st.session_state.messages.append({"role":"user","content":user_msg})
    send_plan()
    user_msg = None

# ---------- GPT 正常回答 ----------
if user_msg:
    with st.chat_message("user"): st.markdown(user_msg)
    st.session_state.messages.append({"role":"user","content":user_msg})

    context = "\n\n".join(search(user_msg, k=3))
    sys_prompt = {
        1:"You are in **Understand** phase. Explain e-waste basics clearly.",
        2:"You are in **Control** phase. Discuss and reinforce knowledge.",
        3:"You are in **Improve** phase. Provide actionable circular-economy steps."
    }[st.session_state.stage] + f"\n\nReference:\n{context}"

    full = ""
    with st.chat_message("assistant"):
        holder = st.empty()
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role":"system","content":sys_prompt},
                {"role":"user","content":user_msg}],
            stream=True, temperature=0.7, max_tokens=800
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            for ch in delta:
                full += ch
                holder.markdown(full + "▌")
                time.sleep(0.01)
        holder.markdown(full)
    st.session_state.messages.append({"role":"assistant","content":full})
