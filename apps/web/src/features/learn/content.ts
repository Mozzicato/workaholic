/**
 * The learning section (PRD §46).
 *
 * Seven short pages, written to be read in a couple of minutes each. They are plain data rather
 * than a CMS because they change rarely and should never be able to break the resume workflow.
 *
 * The tone is the product's: concrete, honest about what is uncertain, and unwilling to promise
 * things nobody can promise — no "beat the ATS", no "recruiters spend exactly six seconds".
 */

export type Article = {
  slug: string;
  title: string;
  summary: string;
  minutes: number;
  sections: { heading: string; paragraphs: string[]; list?: string[] }[];
};

export const ARTICLES: Article[] = [
  {
    slug: "what-is-a-resume",
    title: "What is a resume?",
    summary: "What the document is for, and what it is not for.",
    minutes: 3,
    sections: [
      {
        heading: "It is an argument, not an archive",
        paragraphs: [
          "A resume is a short, checkable case that you can do a particular job. It is not a complete record of everything you have ever done — that belongs in your career record, which is what Workaholic keeps for you.",
          "Because it is an argument, everything on it invites a question. A line that says you rebuilt an import job invites “how?”. A line that says you increased revenue by 30% invites “how do you know?”. Write lines you would enjoy being asked about.",
        ],
      },
      {
        heading: "Who reads it, and how",
        paragraphs: [
          "Usually software reads it first, pulling out text to store in a database. Then a person skims it, often quickly, looking for reasons to keep reading.",
          "Both readers want the same thing: plain structure and specific content. Neither is impressed by design.",
        ],
      },
      {
        heading: "How long",
        paragraphs: [
          "One page is right for almost everyone early in their career. Two pages is normal after several years. Length is a consequence of having more to say, not a target to reach.",
        ],
      },
    ],
  },
  {
    slug: "resume-vs-cv",
    title: "Resume or CV?",
    summary: "The same words mean different things in different countries.",
    minutes: 2,
    sections: [
      {
        heading: "The short version",
        paragraphs: [
          "In the US and Canada, a résumé is a short targeted document and a CV is a long academic one listing publications, teaching and grants.",
          "In the UK, Ireland, much of Europe, Africa, India and Australia, “CV” simply means the short document — what an American would call a resume.",
        ],
      },
      {
        heading: "What to do about it",
        paragraphs: [
          "Use whichever word the advert uses, and send the short document unless you are applying for an academic or research post.",
          "If you are applying internationally, the safest choice is a clear, short document with standard section headings. That is readable as either.",
        ],
      },
      {
        heading: "What about photos, age, marital status?",
        paragraphs: [
          "Conventions differ sharply by country, and in some places including a photo or date of birth invites discrimination that laws elsewhere exist to prevent. When in doubt, leave them off: no employer has ever rejected someone for omitting their date of birth.",
        ],
      },
    ],
  },
  {
    slug: "what-is-ats",
    title: "What is an ATS?",
    summary: "What applicant tracking systems actually do, and what they do not.",
    minutes: 4,
    sections: [
      {
        heading: "It is a database, not a judge",
        paragraphs: [
          "An applicant tracking system stores applications so a company can manage them. It parses your file into fields — name, contact details, employers, dates, skills — and makes them searchable.",
          "The myth is that it scores you and bins you. Mostly it does not. What it does do is fail to read documents that are hard to parse, which has the same effect for you: a recruiter searching for “Python” never sees your application, because your skills ended up inside an image or a table cell.",
        ],
      },
      {
        heading: "What actually causes problems",
        paragraphs: ["The failures are boring and mechanical:"],
        list: [
          "Text inside images or logos, which extracts as nothing",
          "Multi-column layouts read out of order",
          "Important details in a page header or footer, which some parsers drop",
          "Tables whose cells are read in an unexpected sequence",
          "Unusual section headings a parser does not recognise",
          "Dates written so inconsistently that no history can be built",
        ],
      },
      {
        heading: "About scores",
        paragraphs: [
          "Be sceptical of any tool — including this one — that gives you an “ATS score” and implies it predicts what an employer's system will do. Employers run different products, configured differently, with different search terms for every role.",
          "Workaholic's ATS Compatibility Score checks properties your document demonstrably has: that its text extracts, that its headings are standard, that its dates are readable, that the words the advert used actually appear. That is useful. It is not a prediction, and we will not pretend otherwise.",
        ],
      },
      {
        heading: "The one trick that is not a trick",
        paragraphs: [
          "Use the words the advert uses, for the things you have actually done. If they say “REST APIs” and you built REST APIs, write “REST APIs” rather than “web services”. That is not gaming a system; it is answering the question you were asked.",
          "Adding skills you do not have to match keywords is the opposite: it fails at the interview, which is a much more expensive place to fail.",
        ],
      },
    ],
  },
  {
    slug: "writing-better-experience-bullets",
    title: "Writing better experience bullets",
    summary: "The difference between what you were responsible for and what you did.",
    minutes: 4,
    sections: [
      {
        heading: "Start with the action",
        paragraphs: [
          "“Responsible for the nightly import job” describes a job description. “Rewrote the nightly import job to read files in chunks” describes you.",
          "A useful test: could this sentence have been written by someone who held the role but did nothing in it? If yes, it is a duty, not an achievement.",
        ],
      },
      {
        heading: "Say what changed",
        paragraphs: [
          "Most bullets stop at the action. The interesting half is the consequence: it stopped failing, it went from twenty minutes to five, the team stopped doing it by hand.",
          "You do not need a percentage. “The nightly import stopped failing, which it had done about twice a week” is concrete, checkable and honest, and it is worth more than an invented “improved reliability by 40%”.",
        ],
      },
      {
        heading: "Keep your own words",
        paragraphs: [
          "Corporate vocabulary — leveraged, spearheaded, synergies — makes every candidate sound identical and tells a reader nothing. Plain description of specific work is rarer and more memorable.",
        ],
      },
      {
        heading: "A worked example",
        paragraphs: [
          "Before: “Responsible for various backend tasks and improving system performance.”",
          "After: “Changed the invoice import to read large files in chunks, after it had been timing out on anything over about 50MB.”",
          "The second is longer, and better, because it can be discussed.",
        ],
      },
    ],
  },
  {
    slug: "how-to-describe-projects",
    title: "How to describe projects",
    summary: "Side projects and coursework, written so they count.",
    minutes: 3,
    sections: [
      {
        heading: "Answer four questions",
        paragraphs: ["A project entry that works usually answers these, briefly:"],
        list: [
          "What is it? One sentence a stranger would understand.",
          "Why did you build it? A real reason beats “to learn React”.",
          "What did you build, specifically? Which parts are yours.",
          "What came of it? Who used it, what you learned, what broke.",
        ],
      },
      {
        heading: "Small and real beats big and imaginary",
        paragraphs: [
          "A bus tracker forty students actually used is more persuasive than an unfinished clone of a famous app. Usage, however small, is evidence. “40 students used it in the first week” is a fact a reader can picture.",
        ],
      },
      {
        heading: "Be exact about your part",
        paragraphs: [
          "For group projects and coursework, say what you did rather than what the team did. Claiming a team's work is the single easiest thing to catch in an interview, because the follow-up question is always “how did you build that?”.",
        ],
      },
    ],
  },
  {
    slug: "how-to-quantify-achievements",
    title: "How to quantify achievements",
    summary: "Finding real numbers, and what to do when there are none.",
    minutes: 4,
    sections: [
      {
        heading: "Numbers you probably already have",
        paragraphs: ["Most people think they have no metrics. Usually they have several:"],
        list: [
          "How often something happened before, and after — “failed twice a week”, “ran nightly”",
          "How long something took — “twenty minutes down to five”",
          "How much of something — “about 40 students”, “around 200 invoices a day”",
          "How many people — team size, users, students, customers you dealt with",
          "How big — file sizes, row counts, number of screens or endpoints",
        ],
      },
      {
        heading: "Approximate is fine; invented is not",
        paragraphs: [
          "“About 40” and “roughly twice a week” are honest and useful. They signal you remember the real situation.",
          "A precise-looking number you cannot source — “improved performance by 37%” — is worse than no number at all, because the obvious interview question is how you measured it.",
        ],
      },
      {
        heading: "When there is genuinely no number",
        paragraphs: [
          "Say what changed in words. “Before, deployments were done by hand from someone's laptop; after, they ran from CI” has no metric and is completely clear.",
          "This is also why Workaholic asks you questions instead of filling gaps for you: a number you supply is evidence, and one we invent is a liability.",
        ],
      },
    ],
  },
  {
    slug: "common-resume-mistakes",
    title: "Common resume mistakes",
    summary: "The ones that cost people interviews, in rough order.",
    minutes: 4,
    sections: [
      {
        heading: "Claiming things you cannot discuss",
        paragraphs: [
          "The most expensive mistake is not a typo — it is a line you cannot back up. Every claim is a promise to talk about it for five minutes under mild pressure.",
        ],
      },
      {
        heading: "Duties instead of work",
        paragraphs: [
          "A list of responsibilities reads like the advert you answered rather than the person answering it. Say what you did.",
        ],
      },
      {
        heading: "Design that fights the reader",
        paragraphs: [
          "Two columns, icons instead of labels, skill ratings out of five, a photo, a colour scheme. None of it helps a parser, and none of it substitutes for specifics.",
          "Skill bars deserve special mention: “Python ●●●●○” means nothing to anyone. Four out of five compared to whom?",
        ],
      },
      {
        heading: "One resume for everything",
        paragraphs: [
          "Sending the same document to every job means it leads with whatever you happened to write first. Reordering it so the relevant work comes first costs a minute and changes what a skimming reader sees.",
        ],
      },
      {
        heading: "Small things that still matter",
        paragraphs: [],
        list: [
          "An email address you no longer read",
          "Dates that disagree with each other",
          "A file named resume-final-v3-ACTUAL.pdf",
          "Spelling the company's name wrong in a cover letter",
          "No way to contact you at all — it happens more than you would think",
        ],
      },
    ],
  },
];

export function findArticle(slug: string): Article | undefined {
  return ARTICLES.find((article) => article.slug === slug);
}
