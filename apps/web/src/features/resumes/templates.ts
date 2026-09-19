import type { ResumeTemplate } from "./api";

export type TemplateInfo = {
  key: ResumeTemplate;
  name: string;
  description: string;
  bestFor: string;
  /** Short facts a person can choose by. Only true ones: each is checked against the renderer. */
  traits: string[];
  /** Two columns look modern but some older applicant-tracking systems read them out of order. */
  twoColumns?: boolean;
};

/**
 * Every template, in the order the gallery shows them. The images in /public/templates are
 * printed by the real renderer (apps/api/scripts/render_template_previews.py), so what a card
 * shows is what a download looks like.
 */
export const TEMPLATES: readonly TemplateInfo[] = [
  {
    key: "classic",
    name: "Classic",
    description: "A book serif, ruled headings and one line per role. Calm and easy to scan.",
    bestFor: "Students and new graduates",
    traits: ["Education first", "One column"],
  },
  {
    key: "harvard",
    name: "Harvard",
    description: "The careers-office standard: Times-style type, capital headings, italic roles.",
    bestFor: "Any field, any level",
    traits: ["Education first", "One column"],
  },
  {
    key: "engineering",
    name: "Engineering",
    description: "Plain, dense and skills-first, the way engineering recruiters like it.",
    bestFor: "Tech and engineering",
    traits: ["Skills first", "One column"],
  },
  {
    key: "modern",
    name: "Modern",
    description: "A clean sans-serif with teal headings and small contact icons.",
    bestFor: "Tech, business and product",
    traits: ["Experience first", "One column"],
  },
  {
    key: "bold",
    name: "Bold",
    description: "A heavy name, and headings on a warm band that stand out on paper.",
    bestFor: "Career fairs and printed copies",
    traits: ["Education first", "One column"],
  },
  {
    key: "minimal",
    name: "Minimal",
    description: "Lots of white space, quiet grey headings, nothing ruled.",
    bestFor: "Design, product and creative roles",
    traits: ["Experience first", "One column"],
  },
  {
    key: "executive",
    name: "Executive",
    description: "Your name on a dark band, with understated gold-accented headings.",
    bestFor: "Experienced and senior candidates",
    traits: ["Experience first", "One column"],
  },
  {
    key: "sidebar",
    name: "Sidebar",
    description: "Work on the left; education, skills and certificates in a side column.",
    bestFor: "Experienced candidates with a lot to show",
    traits: ["Two columns"],
    twoColumns: true,
  },
  {
    key: "compact",
    name: "Compact",
    description: "Tighter spacing in a sans-serif, to fit more on one page.",
    bestFor: "A long record on one page",
    traits: ["Experience first", "One column"],
  },
  {
    key: "standard",
    name: "Standard",
    description: "Roomy and conventional, with a serif and ruled capital headings.",
    bestFor: "Any field",
    traits: ["Experience first", "One column"],
  },
  {
    key: "academic",
    name: "Academic",
    description: "Education leads, and qualifications get room to breathe.",
    bestFor: "Postgraduate and research applications",
    traits: ["Education first", "One column"],
  },
];

export function templateInfo(key: ResumeTemplate): TemplateInfo {
  return TEMPLATES.find((template) => template.key === key) ?? TEMPLATES[0];
}

export function templateImage(key: ResumeTemplate): string {
  return `/templates/${key}.webp`;
}
