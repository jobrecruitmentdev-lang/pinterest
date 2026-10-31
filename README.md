# 📌 Pinterest 7-Account Automation System (Playwright Stealth)

Ye automation system aapko ek hi post (Image, Title, Description, Link aur Hashtags) ko apne sabhi **7 Pinterest accounts** par automatically aur safely publish karne ki suvidha deta hai.

---

## ⚡ Quick Start: Sabse Aasan Tareeqa (.bat Launcher)

### Step 1: `.env` me apni 7 Session IDs Daalein (One-Time Setup)
1. [.env](file:///C:/hk/Pinterest%20automation/.env) file ko Notepad me open karein.
2. Har account ki Pinterest session cookie (`_pinterest_sess`) paste kar dein:
   ```env
   SESSION_ID_1=apki_pehli_session_id
   BOARD_NAME_1=My Board 1  # (Optional: khali chhodenge toh pehla board lega)

   SESSION_ID_2=apki_doosri_session_id
   BOARD_NAME_2=
   ...
   SESSION_ID_7=apki_saatvi_session_id
   BOARD_NAME_7=
   ```
3. File save karke close kar dein.

---

### Step 2: [START_POSTING.bat](file:///C:/hk/Pinterest%20automation/START_POSTING.bat) Par Double Click Karein
Ab jab bhi aapko nayi post karni ho, bas [START_POSTING.bat](file:///C:/hk/Pinterest%20automation/START_POSTING.bat) par **Double-Click** karein!

Aapke samne ek interactive screen khulegi jo aap se step-by-step maangegi:
1. **Photo Path:** Photo ko mouse se pakad kar window me drag & drop kar dein (ya path type karein).
2. **Title:** Pin ka title likhein.
3. **Description:** Pin ka caption likhein.
4. **Hashtags:** Apne tags likhein (e.g., `#homedecor #aesthetic #diy`).
5. **Destination Link:** Apni website / blog ka link likhein.

Saari details enter karne ke baad **Pre-Flight Confirmation** aayega. Bas **`Y`** dabayein aur script ek ke baad ek sabhi 7 accounts par post karna start kar degi! 🚀

---

## 🛡️ Anti-Ban Protections

* **Playwright Stealth:** Anti-bot & Cloudflare detection ko bypass karta hai.
* **Smart Cooldown Delay:** Har account ke post hone ke baad 30–45 seconds ka random human delay deta hai taaki botnet flag na ho.
* **Invisible Image Hash Variation:** Same image binary 7 alag accounts pe duplicate flag na ho, isliye har account ke liye 1 micro-pixel vary karke unique hash banti hai bina picture quality kharab kiye.
* **Debug Screenshots:** Agar kisi account ka session expire ho gaya ho, toh [debug_screenshots/](file:///C:/hk/Pinterest%20automation/debug_screenshots) me screenshot save ho jata hai taaki aap dekh sakein.

---

## 📂 File Structure

* [START_POSTING.bat](file:///C:/hk/Pinterest%20automation/START_POSTING.bat) — Double-click one-shot launcher.
* [.env](file:///C:/hk/Pinterest%20automation/.env) — 7 Accounts ki Session IDs aur boards.
* [interactive_runner.py](file:///C:/hk/Pinterest%20automation/interactive_runner.py) — Interactive input aur validation handler.
* [pinterest_poster.py](file:///C:/hk/Pinterest%20automation/pinterest_poster.py) — Browser automation engine.
* [utils/stealth_browser.py](file:///C:/hk/Pinterest%20automation/utils/stealth_browser.py) — Stealth context & cookie injector.
* [utils/image_helper.py](file:///C:/hk/Pinterest%20automation/utils/image_helper.py) — Image checker & hash modifier.
