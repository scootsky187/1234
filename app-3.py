import streamlit as st
import random
import json
from datetime import datetime
import os

# ====================== CORE CLASSES ======================

class Player:
    def __init__(self, name="Hero", income=994, difficulty="normal", career="ssi"):
        self.name = name
        self.avatar = "🧑"  # Default avatar, customizable
        self.base_income = income
        self.income = income
        self.difficulty = difficulty.lower()
        self.career = career.lower()
        
        if self.difficulty == "easy":
            self.balance = 500.0
            self.income += 150
        elif self.difficulty == "hard":
            self.balance = 50.0
            self.income -= 50
        else:
            self.balance = 200.0
        
        self.month = 1
        self.week = 1  # 1-4 per month
        self.health = 100
        self.reputation = 50
        self.skills = {"Budgeting": 1, "Saving": 1, "Negotiation": 1}
        # Skill Tree Branches (Tiered progression)
        self.skill_tree = {
            "Budgeting": {"level": 1, "max": 5, "bonus": "reduces grocery/utility costs by 5% per level"},
            "Saving": {"level": 1, "max": 5, "bonus": "monthly interest/savings buffer"},
            "Negotiation": {"level": 1, "max": 5, "bonus": "better aid & deals"},
            # Tier 2 Branches (unlocked at level 3+)
            "Debt Mastery": {"level": 0, "max": 4, "bonus": "reduces late fees & debt stress"},
            "Investment Basics": {"level": 0, "max": 4, "bonus": "small passive gains"},
            # Tier 3 (high rep)
            "Entrepreneur Path": {"level": 0, "max": 3, "bonus": "side gig multipliers"},
            "Legacy Planning": {"level": 0, "max": 3, "bonus": "long-term reputation & health"}
        }
        self.inventory = []
        self.community_visits = 0
        self.unlocked_events = []
        self.history = []  # For charts: (month, balance, health, rep)
        self.earnings_this_month = 0  # For part-time job calculations
        
        # Weekly Appointments / Calendar
        self.appointments = []  # List of dicts: {"week": int, "task": str, "completed": bool}
        self.organization_score = 0
        
        # Bill Management
        self.bills = {
            "Rent": {"amount": 350, "due_week": 1, "paid": False, "auto_pay": False},
            "Utilities": {"amount": 90, "due_week": 2, "paid": False},
            "Groceries": {"amount": 220, "due_week": 1, "paid": False},
            "Transportation": {"amount": 60, "due_week": 3, "paid": False},
            "Phone/Internet": {"amount": 45, "due_week": 2, "paid": False},
            "Health/Misc": {"amount": 50, "due_week": 4, "paid": False},
        }
        self.rent_auto_pay = False  # Discount if auto-pay
        
        # Monthly Bingo
        self.bingo_board = [[False for _ in range(3)] for _ in range(3)]
        self.bingo_tasks = [
            "Paid bills on time", "Tracked all spending", "Attended community resource",
            "Saved at least $20", "Used negotiation skill", "Healthy meal prep",
            "Reviewed budget", "Helped a neighbor", "No impulse purchases"
        ]
        self.completed_bingo_lines = 0

    def setup_rent_option(self, auto_pay):
        self.rent_auto_pay = auto_pay
        if auto_pay:
            self.bills["Rent"]["amount"] = 340  # Small discount
            self.bills["Rent"]["auto_pay"] = True

    def apply_part_time_earnings(self, earnings):
        """SSI-style: First $85 disregarded, then $1 reduction per $2 earned."""
        if self.career != "part_time":
            self.income = self.base_income
            return earnings
        
        self.earnings_this_month += earnings
        disregarded = min(85, self.earnings_this_month)
        countable = max(0, self.earnings_this_month - 85)
        reduction = countable / 2
        self.income = max(0, self.base_income - reduction)
        return earnings

    def receive_income(self):
        self.balance += self.income
        return f"Month {self.month} Income (1st): +${self.income}"

    def pay_bill(self, bill_name):
        if bill_name in self.bills and not self.bills[bill_name]["paid"]:
            amount = self.bills[bill_name]["amount"]
            self.balance -= amount
            self.bills[bill_name]["paid"] = True
            if self.balance < 0:
                self.health = max(0, self.health - 10)
            return amount
        return 0

    def reset_bills(self):
        for bill in self.bills.values():
            bill["paid"] = False
        if self.rent_auto_pay:
            self.bills["Rent"]["paid"] = True  # Auto-paid on 1st

    def access_community_resources(self):
        self.community_visits += 1
        aid_amount = 0
        is_free_event = random.random() > 0.6 or self.reputation > 70
        
        if self.balance < 150 or self.health < 60 or is_free_event:
            aid_amount = random.randint(30, 70) if is_free_event else random.randint(40, 80)
            self.balance += aid_amount
            health_gain = 5 if is_free_event else 12
            rep_gain = 15 if is_free_event else 5
            self.health = min(100, self.health + health_gain)
            self.reputation = min(100, self.reputation + rep_gain)
            msg = f"Community Aid: +${aid_amount}"
            if is_free_event:
                msg += " (Free event - Reputation boosted!)"
            return aid_amount, msg
        return 0, "Community resources not needed this period."

    def add_to_history(self):
        self.history.append({
            "month": self.month,
            "balance": round(self.balance, 2),
            "health": self.health,
            "reputation": self.reputation
        })

    def reset_bingo(self):
        self.bingo_board = [[False for _ in range(3)] for _ in range(3)]
        self.completed_bingo_lines = 0

    def reset_weekly_appointments(self):
        """Reset appointments for new month"""
        self.appointments = []
        self.organization_score = 0

    def add_appointment(self, task):
        self.appointments.append({
            "week": self.week,
            "task": task,
            "completed": False
        })
        return f"Added appointment: {task} (Week {self.week})"

    def complete_appointment(self, idx):
        if 0 <= idx < len(self.appointments):
            self.appointments[idx]["completed"] = True
            self.organization_score += 1
            return True
        return False

    def get_organization_bonus(self):
        """Bonus based on completed appointments"""
        completed = sum(1 for a in self.appointments if a["completed"])
        bonus = min(25, completed * 4)  # +rep/health
        self.reputation = min(100, self.reputation + bonus)
        self.health = min(100, self.health + bonus // 2)
        return bonus

    def upgrade_skill(self, skill_name):
        """Upgrade skill and apply tree effects"""
        if skill_name in self.skills:
            if self.skills[skill_name] < 5:
                self.skills[skill_name] = min(5, self.skills[skill_name] + 1)
                # Check for tier 2 unlocks
                if self.skills[skill_name] >= 3 and skill_name in ["Budgeting", "Saving", "Negotiation"]:
                    if skill_name == "Budgeting" and self.skill_tree["Debt Mastery"]["level"] == 0:
                        self.skill_tree["Debt Mastery"]["level"] = 1
                    elif skill_name == "Saving" and self.skill_tree["Investment Basics"]["level"] == 0:
                        self.skill_tree["Investment Basics"]["level"] = 1
                    elif skill_name == "Negotiation" and self.skill_tree["Entrepreneur Path"]["level"] == 0:
                        self.skill_tree["Entrepreneur Path"]["level"] = 1
                return True
        elif skill_name in self.skill_tree and self.skill_tree[skill_name]["level"] < self.skill_tree[skill_name]["max"]:
            if self.reputation >= 60:  # Higher tier requirement
                self.skill_tree[skill_name]["level"] += 1
                return True
        return False

    def get_skill_bonuses(self):
        """Apply passive bonuses based on skill tree levels"""
        budgeting_lvl = self.skills.get("Budgeting", 1)
        if budgeting_lvl > 1:
            # 5% reduction per level above 1 on Groceries and Utilities
            discount = (budgeting_lvl - 1) * 0.05
            for bill_name in ["Groceries", "Utilities"]:
                if bill_name in self.bills:
                    base = {"Groceries": 220, "Utilities": 90}[bill_name]
                    self.bills[bill_name]["amount"] = round(base * (1 - discount), 2)

        saving_lvl = self.skills.get("Saving", 1)
        if saving_lvl > 1:
            # Small monthly interest on positive balance
            if self.balance > 0:
                interest = round(self.balance * 0.005 * (saving_lvl - 1), 2)
                self.balance += interest
                return f"Skill bonuses active — Budgeting saves on bills, Saving earned ${interest} interest"

        return "Skill bonuses active"

    def check_bingo_wins(self):
        lines = 0
        # Rows
        for row in self.bingo_board:
            if all(row):
                lines += 1
        # Columns
        for col in range(3):
            if all(self.bingo_board[row][col] for row in range(3)):
                lines += 1
        # Diagonals
        if all(self.bingo_board[i][i] for i in range(3)):
            lines += 1
        if all(self.bingo_board[i][2-i] for i in range(3)):
            lines += 1
        self.completed_bingo_lines = lines
        return lines

class Quest:
    def __init__(self):
        self.quests = [
            {
                "title": "Grocery Challenge",
                "description": "Your fridge is low. Choose how to shop this week.",
                "choices": [
                    {"text": "Buy cheap basics only", "cost": -45, "effect": "health+10, budgeting+1"},
                    {"text": "Splurge on treats & snacks", "cost": -110, "effect": "health-5"},
                    {"text": "Use coupons, meal plan & shop sales", "cost": -65, "effect": "budgeting+2, reputation+5"}
                ]
            },
            {
                "title": "Unexpected Bill",
                "description": "Car repair or major maintenance needed (~$150).",
                "choices": [
                    {"text": "Pay full from savings (premium service)", "cost": -150, "effect": "health+20, reputation+15"},
                    {"text": "Ignore it and hope", "cost": 0, "effect": "health-30"},
                    {"text": "Negotiate payment plan", "cost": -75, "effect": "negotiation+1, reputation+15"}
                ]
            },
            {
                "title": "Side Gig Opportunity",
                "description": "A neighbor offers odd jobs for extra cash. (Part-time earnings affect SSI benefits if applicable)",
                "choices": [
                    {"text": "Take the gig (extra effort)", "cost": 80, "effect": "saving+1, reputation+10"},
                    {"text": "Decline, rest instead", "cost": 0, "effect": "health+5"},
                    {"text": "Negotiate better pay", "cost": 120, "effect": "negotiation+2"}
                ]
            },
            {
                "title": "Community Event",
                "description": "Local free workshop on budgeting/finance.",
                "choices": [
                    {"text": "Attend and network", "cost": -10, "effect": "budgeting+2, reputation+15"},
                    {"text": "Skip it", "cost": 0, "effect": "health-5"},
                    {"text": "Volunteer to help run it", "cost": 20, "effect": "reputation+20, negotiation+1"}
                ]
            },
            {
                "title": "Emergency Medical",
                "description": "Minor health issue arises (copay or meds).",
                "choices": [
                    {"text": "Pay out of pocket (quality care)", "cost": -60, "effect": "health+25"},
                    {"text": "Delay care", "cost": 0, "effect": "health-25"},
                    {"text": "Seek low-cost clinic / aid", "cost": -25, "effect": "health+10, reputation+10"}
                ]
            },
            {
                "title": "Utility Spike",
                "description": "Higher than expected bill due to weather.",
                "choices": [
                    {"text": "Pay full (reliable service)", "cost": -85, "effect": "health+10, reputation+8"},
                    {"text": "Partial pay & risk shutoff", "cost": -40, "effect": "health-15"},
                    {"text": "Apply for assistance program", "cost": -30, "effect": "negotiation+1, reputation+12"}
                ]
            }
        ]
        self.unlockable_quests = [
            {
                "title": "Major Investment Opportunity",
                "description": "A low-risk savings program or skill course is available (high reputation).",
                "choices": [
                    {"text": "Invest/save aggressively", "cost": -200, "effect": "health+15, saving+3"},
                    {"text": "Skip for now", "cost": 0, "effect": ""},
                    {"text": "Research & partially commit", "cost": -80, "effect": "budgeting+2, reputation+10"}
                ]
            }
        ]

    def get_random_quest(self, player):
        if player.reputation > 65 and random.random() > 0.65 and self.unlockable_quests:
            return random.choice(self.unlockable_quests), True
        return random.choice(self.quests), False

def apply_effect(player, effect_str):
    if not effect_str:
        return
    effects = effect_str.split(", ")
    for eff in effects:
        eff = eff.strip()
        try:
            # Extract signed integer: e.g. "health+10" -> +10, "health-25" -> -25
            if "+" in eff:
                sign = 1
                digits = eff.split("+")[-1]
            elif "-" in eff and not eff.startswith("-"):
                sign = -1
                digits = eff.split("-")[-1]
            else:
                continue
            val = int(digits) * sign
            if "health" in eff.lower():
                player.health = max(0, min(100, player.health + val))
            elif "reputation" in eff.lower():
                player.reputation = max(0, min(100, player.reputation + val))
            else:
                for skill in ["budgeting", "saving", "negotiation"]:
                    if skill in eff.lower():
                        key = skill.capitalize()
                        # Cap core skills at 5
                        player.skills[key] = min(5, player.skills.get(key, 1) + abs(val))
                        break
        except (ValueError, IndexError):
            pass

# ====================== STREAMLIT APP ======================

st.set_page_config(page_title="Budget Quest", page_icon="🛡️", layout="wide")
st.title("🛡️ Budget Quest: Financial Hero")
st.markdown("**Learn money management through fun quests on a fixed income!**")

# Session State
if "player" not in st.session_state:
    st.session_state.player = None
if "quest_manager" not in st.session_state:
    st.session_state.quest_manager = None
if "current_quest" not in st.session_state:
    st.session_state.current_quest = None
if "is_unlocked" not in st.session_state:
    st.session_state.is_unlocked = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "messages" not in st.session_state:
    st.session_state.messages = []

def reset_game():
    st.session_state.player = None
    st.session_state.quest_manager = None
    st.session_state.current_quest = None
    st.session_state.is_unlocked = False
    st.session_state.game_over = False
    st.session_state.messages = []

# Leaderboard persistence
LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    # Default leaderboard with Seth L, Jess G, Jeff H
    return {
        "balance": [
            {"name": "Seth L", "score": 1250, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=seth"},
            {"name": "Jess G", "score": 980, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jess"},
            {"name": "Jeff H", "score": 650, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jeff"}
        ],
        "health": [
            {"name": "Seth L", "score": 95, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=seth"},
            {"name": "Jess G", "score": 88, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jess"},
            {"name": "Jeff H", "score": 72, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jeff"}
        ],
        "reputation": [
            {"name": "Seth L", "score": 92, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=seth"},
            {"name": "Jess G", "score": 85, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jess"},
            {"name": "Jeff H", "score": 68, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=jeff"}
        ]
    }

def save_leaderboard(leaderboard):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(leaderboard, f, indent=2)

def update_leaderboard(player):
    lb = load_leaderboard()
    entry = {"name": player.name, "score": int(player.balance), "avatar": player.avatar}
    
    # Update Balance
    lb["balance"].append(entry)
    lb["balance"] = sorted(lb["balance"], key=lambda x: x["score"], reverse=True)[:10]
    
    # Update Health
    entry_h = {"name": player.name, "score": player.health, "avatar": player.avatar}
    lb["health"].append(entry_h)
    lb["health"] = sorted(lb["health"], key=lambda x: x["score"], reverse=True)[:10]
    
    # Update Reputation
    entry_r = {"name": player.name, "score": player.reputation, "avatar": player.avatar}
    lb["reputation"].append(entry_r)
    lb["reputation"] = sorted(lb["reputation"], key=lambda x: x["score"], reverse=True)[:10]
    
    save_leaderboard(lb)
    return lb

# Sidebar - Setup / Controls
with st.sidebar:
    st.header("Game Setup")
    if st.button("New Game", type="primary"):
        reset_game()
    
    if st.session_state.player is None:
        name = st.text_input("Hero Name", value="Budget Hero")
        
        # Image-based Avatar customization
        avatar_options = [
            {"name": "Classic Hero", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=hero"},
            {"name": "Warrior", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=warrior"},
            {"name": "Mage", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=mage"},
            {"name": "Explorer", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=explorer"},
            {"name": "Leader", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=leader"},
            {"name": "Guardian", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=guardian"},
            {"name": "Innovator", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=innovator"},
            {"name": "Dreamer", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=dreamer"},
            {"name": "Strategist", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=strategist"},
            {"name": "Champion", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=champion"},
        ]
        
        avatar_choice = st.selectbox(
            "Choose Your Avatar", 
            options=[opt["name"] for opt in avatar_options],
            index=0
        )
        selected_avatar = next(opt for opt in avatar_options if opt["name"] == avatar_choice)
        
        difficulty = st.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
        
        st.subheader("Career Path")
        career = st.selectbox("Choose your path:", 
                            ["SSI-Only (Fixed Income)", "Part-Time Job", "Student (Lower Base + Aid)"], 
                            index=0)
        
        st.subheader("Rent Setup (1st of month)")
        rent_option = st.radio("Rent payment preference:", 
                              ["Manual Pay ($350)", "Auto-Pay with discount ($340)"], 
                              index=1)
        
        if st.button("Start Adventure"):
            diff_lower = difficulty.lower()
            career_lower = "ssi" if "SSI" in career else "part_time" if "Part-Time" in career else "student"
            
            base_inc = 994
            if career_lower == "student":
                base_inc = 750  # Lower base + potential aid in quests
            
            player = Player(name=name, income=base_inc, difficulty=diff_lower, career=career_lower)
            player.avatar = selected_avatar["url"]  # Store image URL
            player.setup_rent_option(rent_option == "Auto-Pay with discount ($340)")
            st.session_state.player = player
            st.session_state.quest_manager = Quest()
            st.session_state.messages.append(f"🌟 Game started on **{difficulty}** difficulty as **{career}**! Income on the 1st.")
            st.rerun()

# Main Area
if st.session_state.player is None:
    st.info("👈 Start a new game from the sidebar to begin your financial adventure!")
    
    # === Intro & Real Challenges Section ===
    st.markdown("## 💡 Why Budgeting Matters")
    st.markdown("""
    **Many people struggle with money management.** Without good budgeting skills, common barriers include:
    
    - **Inflation & rising costs**: 37% of people cite prices as their top financial challenge.
    - **Living paycheck-to-paycheck**: Over 70% of Americans report financial stress and anxiety about money.
    - **Lack of emergency savings**: Many have little buffer for unexpected bills, leading to debt cycles and health stress.
    """)
    
    st.subheader("💰 Money Saving Tips to Get Started")
    st.markdown("""
    1. **Track every dollar** — Awareness is the first step to control.
    2. **Use the 50/30/20 rule**: 50% needs, 30% wants, 20% savings/debt.
    3. **Build a small emergency fund** — Even $20–50/month adds up.
    4. **Seek community resources** early — Food banks, utility aid can bridge gaps.
    5. **Celebrate small wins** — Consistency beats perfection.
    """)
    
    st.markdown("""
    ### How to Play
    - Manage a fixed monthly income (SSI-style)
    - Handle realistic expenses
    - Make choices in quests that affect your balance, health & reputation
    - Use community resources wisely
    - Survive 6+ months and build skills!
    """)
else:
    player = st.session_state.player
    qm = st.session_state.quest_manager
    
    # Top Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Balance", f"${player.balance:.2f}", delta=None)
    with col2:
        st.metric("Health", f"{player.health}%")
    with col3:
        st.metric("Reputation", f"{player.reputation}")
    with col4:
        st.metric("Month / Week", f"{player.month} / {player.week}")
    
    # Display avatar image
    st.markdown(f"**Your Hero:**")
    st.image(player.avatar, width=120)
    st.markdown(f"**{player.name}**")
    
    # Progress Charts
    if player.history:
        st.subheader("Progress Over Time")
        chart_data = {"Month": [h["month"] for h in player.history],
                      "Balance": [h["balance"] for h in player.history],
                      "Health": [h["health"] for h in player.history]}
        st.line_chart(chart_data, x="Month", y=["Balance", "Health"])
    
    # Leaderboards
    st.subheader("🏆 Global Leaderboards")
    lb = load_leaderboard()
    
    tab1, tab2, tab3 = st.tabs(["💰 Most Money", "❤️ Most Health", "⭐ Most Reputation"])
    
    with tab1:
        st.write("**Top Balance**")
        for i, entry in enumerate(lb["balance"][:5], 1):
            st.image(entry.get('avatar', 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'), width=50)
            st.write(f"{i}. **{entry['name']}** — ${entry['score']}")
    
    with tab2:
        st.write("**Top Health**")
        for i, entry in enumerate(lb["health"][:5], 1):
            st.image(entry.get('avatar', 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'), width=50)
            st.write(f"{i}. **{entry['name']}** — {entry['score']}%")
    
    with tab3:
        st.write("**Top Reputation**")
        for i, entry in enumerate(lb["reputation"][:5], 1):
            st.image(entry.get('avatar', 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'), width=50)
            st.write(f"{i}. **{entry['name']}** — {entry['score']}")
    
    # Payment Tracker & Bill Options
    st.subheader("📋 Payment Tracker")
    st.markdown("**Bills due this month (income on 1st)** - Pay **before due week** to avoid **15% late fees**!")
    
    unpaid = [b for b, info in player.bills.items() if not info.get("paid", False)]
    if unpaid:
        st.warning(f"**Unpaid bills:** {', '.join(unpaid)}")
    else:
        st.success("✅ All bills paid this month!")
    
    st.caption("💡 **Color Guide:** Green = Due soon (Week 1-2) | Yellow = Mid-month | Orange = Later")
    
    # Bill payment buttons with color-coded due dates
    cols = st.columns(3)
    for idx, (bill_name, info) in enumerate(player.bills.items()):
        with cols[idx % 3]:
            due_week = info.get("due_week", 1)
            amount = info['amount']
            
            # Color coding
            if due_week <= 2:
                color = "🟢"  # Early
            elif due_week == 3:
                color = "🟡"  # Mid
            else:
                color = "🟠"  # Late in month
            
            if not info.get("paid", False):
                btn_label = f"{color} Pay {bill_name} (${amount}) - Due Week {due_week}"
                if st.button(btn_label, key=f"pay_{bill_name}_{player.month}"):
                    paid_amt = player.pay_bill(bill_name)
                    if paid_amt > 0:
                        st.session_state.messages.append(f"✅ Paid {bill_name} on time: -${paid_amt}")
                        st.rerun()
            else:
                st.success(f"✅ {bill_name} (Paid)")
    
    # Weekly Calendar & Appointments
    st.subheader("📅 Weekly Calendar & Appointments")
    st.markdown("**Plan your week!** The more organized you are (appointments scheduled & completed), the higher your Reputation.")
    
    # Auto-suggestions (limited to 4 per week)
    st.markdown("**💡 Suggested Appointments** (up to 4 - choose wisely to stay on track):")
    suggested_tasks = [
        "Pay upcoming bills on time",
        "Budget review & track spending",
        "Job search or side gig hunt",
        "Community resource visit",
        "Healthy meal planning & grocery prep",
        "Self-care / stress management",
        "Review skill tree progress",
        "Savings goal check-in"
    ]
    
    # Limit to first 4 suggestions
    display_suggestions = suggested_tasks[:4]
    
    cols_sug = st.columns(2)
    for i, task in enumerate(display_suggestions):
        with cols_sug[i % 2]:
            if st.button(f"📌 {task}", key=f"sug_{player.week}_{i}"):
                # Check if already added this week
                existing = any(a["task"] == task and a["week"] == player.week for a in player.appointments)
                if not existing:
                    msg = player.add_appointment(task)
                    st.session_state.messages.append(msg)
                    st.rerun()
                else:
                    st.info("Already added this week!")
    
    # Add custom appointment
    col_a, col_b = st.columns([3, 1])
    with col_a:
        new_task = st.text_input("➕ Add Custom Appointment/Task", 
                               placeholder="e.g. Doctor appointment, Family time", key="new_task")
    with col_b:
        if st.button("Add to Calendar", key="add_apt"):
            if new_task and new_task.strip():
                msg = player.add_appointment(new_task.strip())
                st.session_state.messages.append(msg)
                st.rerun()
    
    # Display current week's appointments
    st.write(f"**Week {player.week} of Month {player.month}**")
    week_apts = [apt for apt in player.appointments if apt["week"] == player.week]
    if week_apts:
        for i, apt in enumerate(player.appointments):
            if apt["week"] == player.week:
                checked = st.checkbox(apt["task"], value=apt.get("completed", False), key=f"apt_{player.month}_{player.week}_{i}")
                if checked and not apt.get("completed", False):
                    player.complete_appointment(i)
                    st.success(f"✅ Marked complete: {apt['task']}")
                    st.rerun()
    else:
        st.info("No appointments this week yet. Add some above to boost organization!")
    
    # Check calendar prompt + Advance
    calendar_confirmed = st.checkbox("✅ I have reviewed my calendar and appointments", value=False, key="calendar_check")
    if st.button("Advance to Next Week", type="primary"):
        if calendar_confirmed:
            # Weekly progression
            msgs = []
            
            # Weekly income portion
            weekly_income = round(player.income / 4, 2)
            player.balance += weekly_income
            msgs.append(f"💵 Week {player.week} Income: +${weekly_income}")
            
            # Small weekly expenses
            weekly_exp = round(815 / 4, 2)
            player.balance -= weekly_exp
            if player.balance < 0:
                player.health = max(0, player.health - 5)
                msgs.append(f"📉 Weekly living costs: -${weekly_exp}")
            
            # Organization bonus (stronger at end of month)
            if player.week == 4:
                org_bonus = player.get_organization_bonus()
                if org_bonus > 0:
                    msgs.append(f"📅 Strong organization this month! +{org_bonus} Reputation & health boost.")
            
            player.add_to_history()
            
            # Advance week
            player.week += 1
            if player.week > 4:
                player.week = 1
                msgs.append("🌟 **End of Month Summary**")
                player.earnings_this_month = 0

                # Bug fix: Apply skill bonuses before closing the month
                bonus_msg = player.get_skill_bonuses()
                if "earned" in bonus_msg:
                    msgs.append(f"🎓 {bonus_msg}")

                # Bug fix: Check bingo BEFORE reset_bingo so lines are counted correctly
                bingo_lines = player.check_bingo_wins()
                if bingo_lines > 0:
                    bonus = bingo_lines * 15
                    player.reputation = min(100, player.reputation + bonus)
                    player.balance += bingo_lines * 10
                    msgs.append(f"🎉 BINGO! {bingo_lines} lines → +${bingo_lines*10} & +{bonus} Rep!")

                # Bug fix: Handle auto-pay BEFORE late fee sweep so rent isn't double-charged
                if player.rent_auto_pay:
                    if not player.bills["Rent"].get("paid", False):
                        player.pay_bill("Rent")
                        msgs.append("🏠 Rent auto-paid!")

                # Late bills handling
                late_count = 0
                for bname, binfo in list(player.bills.items()):
                    if not binfo.get("paid", False):
                        original_amt = binfo["amount"]
                        late_fee = round(original_amt * 0.15, 2)
                        total_late = original_amt + late_fee
                        player.balance -= total_late
                        binfo["paid"] = True
                        late_count += 1
                        msgs.append(f"⚠️ LATE {bname}: ${total_late:.2f} (penalty applied)")
                
                if late_count > 0:
                    player.health = max(0, player.health - 8 * late_count)
                    player.reputation = max(0, player.reputation - 7 * late_count)
                
                # Community resources
                if random.random() > 0.3:
                    aid, msg = player.access_community_resources()
                    msgs.append(msg)
                
                # End of month bonuses/penalties
                if player.balance > 150:
                    player.reputation = min(100, player.reputation + 8)
                    player.skills["Saving"] = min(5, player.skills.get("Saving", 1) + 1)
                    msgs.append("💰 Solid saving this month!")
                elif player.balance < -50:
                    player.health = max(0, player.health - 10)
                    msgs.append("⚠️ Finances are stressing you out.")

                # Monthly quest
                if random.random() > 0.25:
                    quest, is_unlock = qm.get_random_quest(player)
                    st.session_state.current_quest = quest
                    st.session_state.is_unlocked = is_unlock

                # Leaderboard update every other month
                if player.month % 2 == 0:
                    update_leaderboard(player)
                    msgs.append("🏆 Leaderboard updated with your progress!")

                # Reset monthly state AFTER all checks
                player.reset_bingo()
                player.reset_bills()
                player.reset_weekly_appointments()
                
                player.month += 1

                if player.health <= 0:
                    st.session_state.game_over = True
            
            st.session_state.messages.extend(msgs)
            st.rerun()
        else:
            st.warning("⚠️ Please confirm you've checked your calendar before advancing!")
            st.stop()
    
    # Display Messages
    if st.session_state.messages:
        with st.expander("Recent Events", expanded=True):
            for msg in st.session_state.messages[-8:]:
                st.write(msg)
    
    # Current Quest
    if st.session_state.current_quest:
        quest = st.session_state.current_quest
        st.subheader("🌟 " + ("UNLOCKED EVENT: " if st.session_state.is_unlocked else "QUEST: ") + quest["title"])
        st.write(quest["description"])
        
        st.markdown("**Make your choice:**")
        for i, choice in enumerate(quest["choices"]):
            cost_str = f"${choice['cost']:+.0f}"
            if st.button(f"{choice['text']}  {cost_str}", key=f"choice_{i}"):
                earnings = 0
                if choice["cost"] > 0:
                    earnings = choice["cost"]
                    player.balance += earnings
                    if hasattr(player, 'apply_part_time_earnings'):
                        actual_earnings = player.apply_part_time_earnings(earnings)
                        st.session_state.messages.append(f"💼 Earned ${actual_earnings} (adjusted for benefits)")
                else:
                    player.balance += choice["cost"]
                
                apply_effect(player, choice.get("effect", ""))
                # Award skill points occasionally
                if random.random() > 0.6:
                    st.session_state.messages.append("💪 +1 Skill Point earned from this choice!")
                st.session_state.messages.append(f"✅ Chose: {choice['text']} → Balance now ${player.balance:.2f}")
                st.session_state.current_quest = None
                st.rerun()

    # Skill Tree Section
    st.subheader("🧗 Skill Tree - Build Your Financial Power!")
    st.markdown("**Spend skill points earned from quests & organization on upgrades.** Higher tiers unlock powerful branches.")

    skill_cols = st.columns(3)
    skill_points = sum(max(0, lvl - 1) for lvl in player.skills.values()) + sum(lvl for lvl in [t["level"] for t in player.skill_tree.values()])  # rough points

    with skill_cols[0]:
        st.markdown("**Core Skills**")
        for sk, lvl in player.skills.items():
            st.progress(lvl / 5, text=f"{sk} (Lvl {lvl}/5)")
            if st.button(f"Upgrade {sk}", key=f"up_{sk}", disabled=lvl >= 5):
                if player.upgrade_skill(sk):
                    st.success(f"✅ {sk} upgraded!")
                    st.rerun()

    with skill_cols[1]:
        st.markdown("**Tier 2 Branches**")
        for sk, data in list(player.skill_tree.items())[3:5]:  # Debt & Investment
            st.progress(data["level"] / data["max"], text=f"{sk} (Lvl {data['level']}/{data['max']})")
            if st.button(f"Unlock/Upgrade {sk}", key=f"up2_{sk}", disabled=data["level"] >= data["max"] or player.reputation < 50):
                if player.upgrade_skill(sk):
                    st.success(f"✅ {sk} advanced!")
                    st.rerun()
            st.caption(data["bonus"])

    with skill_cols[2]:
        st.markdown("**Tier 3 Advanced**")
        for sk, data in list(player.skill_tree.items())[5:]:  
            st.progress(data["level"] / data["max"], text=f"{sk} (Lvl {data['level']}/{data['max']})")
            if st.button(f"Unlock/Upgrade {sk}", key=f"up3_{sk}", disabled=data["level"] >= data["max"] or player.reputation < 70):
                if player.upgrade_skill(sk):
                    st.success(f"✅ {sk} advanced!")
                    st.rerun()
            st.caption(data["bonus"])

    # Monthly Bingo Game
    st.subheader("📅 Monthly Financial Bingo")
    st.markdown("Mark off habits you completed this month for big bonuses!")
    
    cols = st.columns(3)
    task_idx = 0
    for i in range(3):
        for j in range(3):
            with cols[j]:
                task = player.bingo_tasks[task_idx]
                checked = player.bingo_board[i][j]
                new_checked = st.checkbox(task, value=checked, key=f"bingo_{player.month}_{i}_{j}")
                if new_checked != checked:
                    player.bingo_board[i][j] = new_checked
                    # Auto-check wins on change
                    lines = player.check_bingo_wins()
                    if lines > player.completed_bingo_lines:
                        st.success(f"🎉 New bingo line! Total lines: {lines}")
                        player.completed_bingo_lines = lines
                        # Confetti visual upgrade
                        st.markdown("""
                        <div style="text-align: center;">
                            <h3>🎊🎉 CONGRATULATIONS! BINGO! 🎉🎊</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        # Simple JS confetti
                        st.markdown("""
                        <script>
                        function throwConfetti() {
                            for(let i = 0; i < 100; i++) {
                                setTimeout(() => {
                                    const confetti = document.createElement('div');
                                    confetti.textContent = ['🎉','🪙','💰','✨'][Math.floor(Math.random()*4)];
                                    confetti.style.position = 'fixed';
                                    confetti.style.left = Math.random()*100 + 'vw';
                                    confetti.style.top = '-10px';
                                    confetti.style.fontSize = '20px';
                                    confetti.style.transition = 'all 3s';
                                    confetti.style.zIndex = '9999';
                                    document.body.appendChild(confetti);
                                    setTimeout(() => {
                                        confetti.style.transform = `translateY(${window.innerHeight + 100}px) rotate(${Math.random()*720}deg)`;
                                        confetti.style.opacity = '0';
                                    }, 50);
                                    setTimeout(() => confetti.remove(), 3500);
                                }, i * 30);
                            }
                        }
                        throwConfetti();
                        </script>
                        """, unsafe_allow_html=True)
                task_idx += 1
    
    # Status Details
    with st.expander("Full Status & Skills"):
        st.write(f"**Career Path:** {player.career.upper()}")
        st.write(f"**Current Monthly Income:** ${player.income:.2f}")
        if player.career == "part_time":
            st.write(f"**Earnings this month:** ${player.earnings_this_month}")
        st.write(f"**Core Skills:** {player.skills}")
        st.write(f"**Skill Tree:** { {k: v['level'] for k,v in player.skill_tree.items()} }")
        st.write(f"**Community visits:** {player.community_visits}")
        if player.inventory:
            st.write(f"**Inventory:** {player.inventory}")
    
    # Game Over / Win Check
    if player.health <= 0 or player.month > 12:
        st.error("💥 Game Over! Health depleted.")
        if st.button("Restart Game"):
            reset_game()
            st.rerun()
    elif player.month > 6 and player.balance > 100 and player.health > 60:
        st.success("🎉 Congratulations! You've successfully managed your finances for several months!")
        if st.button("Continue Playing"):
            pass
        if st.button("New Game"):
            reset_game()
            st.rerun()

# Footer
st.caption("Budget Quest - Educational tool for money management | Customize income/expenses in code for specific clients")
