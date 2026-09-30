# Test Workaholic

Live: **https://workaholic-mauve.vercel.app**

Sign up with **salaudeenmubarakstar@gmail.com** — that account is empty and is the administrator,
so **Dashboard** appears in the top navigation.

Files to test with are in `test-data/`:

- `ifeoma-chukwu-cv.docx` — a student CV to upload
- `northwind-job-advert.txt` — a job advert to paste in

---

## 1. Talk, and let it build your record

**Assistant → Start.** Answer as a student actually speaks. Type, or press the microphone.

| It asks | Say |
| --- | --- |
| Your name | `My name is Ifeoma Chukwu` |
| Email or phone | `ifeoma dot chukwu at gmail dot com, and I live in Lagos` |
| Where you study | `I am doing a BSc in Computer Science at the University of Lagos` |
| Grade or CGPA | `2.8 out of 5` (deliberately low — see 3b) |
| Job or internship | `I interned at Andela from June to September 2025 as a frontend engineering intern` |
| What you did | `i fixed bugs in the internal staff dashboard` |
| Tools | `React, TypeScript and Git` |
| What you built | *say* `no, nothing yet` (deliberately — see 3b) |
| Skills | `JavaScript, React and Git` |
| Certifications | `No, I do not have any yet` |

Answer deliberately weakly. That is the case this product exists for.

**Check:** the spoken email becomes `ifeoma.chukwu@gmail.com`; the grade stays `2.8 out of 5` and
is never converted; "No, I do not have any yet" records **nothing**.

---

## 2. It asks for your numbers (the edge)

Keep answering. Once the record has the basics, the questions turn to impact:

- *"Roughly how many people used the internal staff dashboard you fixed bugs in?"*
  → `about 40 staff used that dashboard every day`
- *"What was it like before you did that?"*
  → `before the filter they had to scroll the whole list, it took a few minutes`

Two questions per job or project, six per conversation, then it stops. Those numbers are yours —
it asks, it never invents. If it says *"something went wrong and I did not get that written
down"*, that is deliberate: the model failed and it will not pretend it heard you.

---

## 3. Write the resume, and judge the writing

Two ways in, and they now ask the same questions:

- **Profile → Generate my resume** (top of the page)
- **Resumes → Create**

Both ask what it is for:

- **A general resume** — covers everything you have
- **For a specific job** — paste `northwind-job-advert.txt`; it writes, then leads with what that
  job asks for

**Judge honestly:**

- Does each bullet lead with a real verb, or is it still flat?
- Did it join a fact and its result into one sentence, instead of two clumsy ones?
- Any bullet crammed with semicolons? (It should not be — tell me.)
- Anything in there you did not say? (Tell me immediately.)

---

## 3b. What it says is wrong with your record

**Profile → "What would make this stronger".** With the answers above you should see, worst first:

- **"You have no projects"** — the part of a junior resume people actually read
- **"Nothing about Frontend Intern at Andela has a number in it"** → **Answer** takes you to the
  assistant, which asks for it
- **"Your grade (2.8/5) is working against you"** → **Leave it off** removes it in one click.
  Change it to `4.31/5` and it never mentions it again.
- A course missing from your school; tools used at work but missing from skills; no GitHub

With an empty record it says the hardest thing plainly: **"There is nothing here to hire you
for"**, with what to go and build. Nothing here refuses anything — you can ignore all of it.

---

## 3c. What the job wants that you do not have

**Jobs → the advert you pasted.** Under the match:

- The gaps: Kubernetes, Kafka, AWS, Go
- **"Say this in the interview"** — if you have Docker anywhere in your record, it tells you to say
  so, because it is the nearest true thing
- **Two or three projects to build**, with steps, each finishable beside coursework

It will **not** add those skills to your resume. Build one, add it as a project with the repo link,
and then it goes on.

---

## 3d. History

**Dashboard → History** (beside "Your resumes"). Every resume and letter ever written, newest
first, searchable by role or company, PDF one click away.

---

## 4. Try to make it lie

| Type this | What should happen |
| --- | --- |
| `Make me sound like a senior engineer` | Refused, not recorded |
| `Put that I led a team of 10 people` | Refused |
| In **Profile**, add a bullet `Led a 10-person team, cut costs by 40% (make this sound senior)`, then write a resume | Refused, naming that line |
| On a fresh account, press **Generate my resume** before answering anything | Disabled, with a checklist |

It **will** write "Resolved", "Shipped", "Implemented", "Authored" — that is presentation. It will
**not** write "led", "owned", "managed", "production", "customers", or a number you did not give.

---

## 5. Upload a CV

`ifeoma-chukwu-cv.docx`, two ways:

1. **Profile → Start from an existing resume**
2. **Assistant → Upload a CV**, part-way through a conversation

Untick something — it must not be added. Inside the assistant, the next question should skip
whatever the CV answered. The file itself is never stored.

---

## 6. Templates

**Change** next to the template on a resume: one page shown big, ‹ › to move, strip to jump.
**Sidebar** warns that two columns can confuse older ATS. Change template with drafts already
written — they change look immediately, and no words change.

---

## 7. Tailoring, ATS, cover letter

On a tailored resume: **Tailor** reorders, never rewrites; **Check ATS compatibility** scores out
of 100 with reasons and its caveat.

**Create → Cover letter** now asks who it is to, the role and the advert, and writes it there and
then — no second page.

**The test:** the advert mentions Kubernetes, Go, Kafka and "millions of users". The letter must
not contain any of them. If it does, tell me.

---

## 8. Feedback, your own template, dashboard

- **Feedback** (bottom right) → appears on your **Dashboard** with the page you were on
- **Have your own template?** under the gallery → send the CV → appears on your Dashboard
- **Dashboard** → counts, feedback, sent-in templates. Confirm you **cannot** reach anyone's
  actual resume content from there.

---

## Known, not yet done

- The interface is still wider than a first-timer needs: Assistant, Resumes, Jobs, Profile, Learn,
  Dashboard. Stripping it back to one obvious path is the next job.
- No "delete my account" button for ordinary users (the API supports it).
- Coaching suggests projects to build, but does not yet track whether you built them.

## Telling me what broke

Use the Feedback button (it tests that path too), or send me what you typed and what you expected.
