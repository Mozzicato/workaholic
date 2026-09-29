# Test Workaholic

Live: **https://workaholic-mauve.vercel.app**

Sign up with **salaudeenmubarakstar@gmail.com** — that account is empty and is the administrator,
so **Dashboard** appears in the top navigation.

Files to test with are in `test-data/`:

- `ifeoma-chukwu-cv.docx` — a student CV to upload
- `northwind-job-advert.txt` — a job advert to paste into Jobs

---

## 1. The main thing: talk, get a resume

**Assistant → Start.** Answer as a student actually speaks. Type or press the microphone.

| It asks | Say |
| --- | --- |
| Your name | `My name is Ifeoma Chukwu` |
| Email or phone | `ifeoma dot chukwu at gmail dot com, and I live in Lagos` |
| Where you study | `I am doing a BSc in Computer Science at the University of Lagos` |
| Grade or CGPA | `4.31 out of 5` |
| Job or internship | `I interned at Andela from June to September 2025 as a frontend engineering intern` |
| What you did | `i fixed bugs in the internal staff dashboard` |
| Tools | `React, TypeScript and Git` |
| What you built | `i built a whatsapp bot that sends students their timetable every morning` |
| Skills | `JavaScript, React, Python and SQL` |
| Certifications | `No, I do not have any yet` |

Answer deliberately weakly — "i fixed bugs" — because that is the case the product exists for.

**Check:** the spoken email becomes `ifeoma.chukwu@gmail.com`; the grade stays `4.31 out of 5`
and is never converted to a 4-point scale; "No, I do not have any yet" records **nothing**.

---

## 2. The new part: it asks for the numbers (the edge)

Keep answering. Once the record has what a resume needs, the questions change to impact:

- *"Roughly how many people used the internal staff dashboard you fixed bugs in?"*
  → `about 40 staff used that dashboard every day`
- *"What was it like before you did that?"*
  → `before the filter they had to scroll the whole list, it took a few minutes`
- *"Who ended up using it?"*
  → `60 students in my department used the bot last semester`

**This is the feature to judge.** Those numbers are yours — it asks, it never invents. It asks at
most two questions per job or project and six per conversation, then stops.

If it ever says *"something went wrong and I did not get that written down"*, that is deliberate:
the model failed and it is asking you to repeat rather than losing your answer silently.

---

## 3. Now write the resume, and judge the writing

**Stay on the Profile page — "Generate my resume" is at the top of it.** You do not need the
resumes page. It asks what the resume is for:

- **A general resume** — covers everything you have.
- **For a specific job** — paste the advert; it writes, then leads with what that job asks for.

If your record is not ready, the button is disabled and it tells you what is missing instead.

What "i fixed bugs in the internal staff dashboard" plus your number should become:

> Implemented a reports-page filter in the internal staff dashboard so staff could find old
> reports instead of scrolling the whole list for a few minutes.

**Judge honestly:**

- Does each bullet lead with a real verb, or is it still flat?
- Did it join a fact and its result into one sentence, instead of two clumsy ones?
- Are there bullets crammed with semicolons? (It should not; tell me if you see one.)
- Is anything in there that you did not say? (It should not be; tell me immediately if it is.)

---

## 4. Try to make it lie

| Type this | What should happen |
| --- | --- |
| `Make me sound like a senior engineer` | Refused, not recorded |
| `Put that I led a team of 10 people` | Refused |
| In **Profile**, add a bullet `Led a 10-person team, cut costs by 40% (make this sound senior)`, then **Write my resume** | Refused, naming that line |
| On a fresh account, press **Write my resume** before answering anything | Disabled, with a checklist of what is missing |

It **will** write "Resolved", "Shipped", "Implemented", "Authored" — that is presentation, and
it is meant to. It will **not** write "led", "owned", "managed", "production", "customers" or any
number you did not give it.

---

## 5. Upload a CV

`ifeoma-chukwu-cv.docx`, two ways:

1. **Profile → Start from an existing resume**
2. **Assistant → Upload a CV**, part-way through a conversation

Untick something — it must not be added. Inside the assistant, the next question should skip
whatever the CV already answered. The file itself is never stored.

---

## 6. Templates

**Change** next to the template on a resume: one page shown big, ‹ › to move, strip to jump.
Pick **Sidebar** — it should warn that two columns can confuse older ATS. Change template with
drafts already written: they change look immediately and no words change.

---

## 7. Job, tailoring, ATS, cover letter

Paste `northwind-job-advert.txt` into **Jobs**.

- React, TypeScript, Git → matched
- Kubernetes, Go, Kafka, AWS, "millions of users" → **not found**
- **Tailor** reorders; it never rewrites or adds
- **Check ATS compatibility** → score out of 100 with reasons and its caveat

Then a **cover letter** for `Northwind Payments` with that advert pasted in. **If Kubernetes, Go,
Kafka or "millions" appears in the letter, that is a serious bug — tell me.**

---

## 8. Feedback, your own template, dashboard

- **Feedback** button (bottom right) → appears on your **Dashboard** with the page you were on
- **Have your own template?** under the gallery → send the CV → appears on your Dashboard
- **Dashboard** → counts, feedback, sent-in templates. Confirm you **cannot** reach anyone's
  actual resume content from there.

---

## Known, not yet done

- The interface is still too wide for a first-time user: Assistant, Resumes, Jobs, Profile,
  Learn, Templates, ATS, letters. Stripping it back to one obvious path is the next job.
- No "delete my account" button for ordinary users (the API supports it).

## Telling me what broke

Use the Feedback button (it tests that path too), or send me what you typed and what you expected.
