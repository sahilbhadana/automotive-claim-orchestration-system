import { Link } from "react-router-dom";
import {
  ArrowRight,
  Banknote,
  CarFront,
  Check,
  ChevronDown,
  CloudLightning,
  ShieldAlert,
  Users,
} from "lucide-react";

const WHEN_TO_FILE = [
  {
    icon: CarFront,
    title: "Accident or collision",
    desc: "The most common claim. One minor accident can become a major expense — file a claim to repair damage to your own vehicle.",
  },
  {
    icon: ShieldAlert,
    title: "Theft",
    desc: "If your vehicle is stolen, a comprehensive policy covers you. The payout equals your vehicle's Insured Declared Value (IDV).",
  },
  {
    icon: CloudLightning,
    title: "Natural & man-made disaster",
    desc: "Fire, cyclones, storms, earthquakes — and vandalism. If a disaster damages your car, you can claim financial assistance.",
  },
  {
    icon: Users,
    title: "Third-party liability",
    desc: "When your car injures someone or damages their property, your insurer compensates the third party up to the sum insured. Mandatory cover under the Motor Vehicles Act, 1988.",
  },
];

const PROCESS_STEPS = [
  {
    title: "Inform your insurer",
    desc: "Report the incident as soon as possible — through the helpline, website, or app. Share the date, time, and location. Delayed reporting may require a written explanation and extra verification.",
  },
  {
    title: "Lodge an FIR",
    desc: "File a First Information Report at the nearest police station for theft, third-party involvement, bodily injury, malicious damage, key loss, or any major damage. Include the vehicle's number plate, the driver's details, and witness names and contacts.",
  },
  {
    title: "Document the incident",
    desc: "Take photos and videos of the damage, collect witness statements, and don't move the vehicle without permission. Visual evidence supports the surveyor's assessment.",
  },
  {
    title: "Vehicle inspection",
    desc: "A qualified surveyor is appointed within 24 hours of registration to assess the damage — either physically at the workshop or accident site, or digitally via live video. Repairs must not begin until the surveyor's assessment is approved.",
  },
  {
    title: "Submit your documents",
    desc: "Provide the completed claim form, policy copy, FIR (where applicable), driving licence, registration certificate, repair estimate, and KYC documents.",
  },
  {
    title: "Choose your repair route",
    desc: "Use a network garage for cashless settlement, or repair anywhere and claim reimbursement with original invoices and payment receipts.",
  },
  {
    title: "Approval",
    desc: "Once the surveyor's report and your documents are verified, the claim is approved and the payable amount determined by your coverage, IDV, deductibles, and depreciation.",
  },
  {
    title: "Track and settle",
    desc: "Follow your claim status online. After the final repair invoice is received, settlement is completed — directly with the garage for cashless, or to your account for reimbursement.",
  },
];

const DOC_SETS: { title: string; docs: string[] }[] = [
  {
    title: "Accident claims",
    docs: [
      "Original insurance policy copy",
      "Vehicle registration certificate (RC)",
      "Valid driving licence",
      "FIR copy (if damage is severe)",
      "Proof of vehicle damage (photos)",
      "Original repair bills (for reimbursement)",
      "Duly filled claim form",
      "Cancelled cheque for payment",
    ],
  },
  {
    title: "Theft claims",
    docs: [
      "FIR and final non-traceable report",
      "Vehicle registration certificate (RC)",
      "Original insurance policy certificate",
      "Driving licence",
      "Original purchase invoice (if return-to-invoice cover)",
      "All original vehicle keys",
      "RC transfer forms (28, 29, 30)",
      "Indemnity bond & subrogation letter",
    ],
  },
  {
    title: "Third-party claims",
    docs: [
      "Photos of the damage",
      "Legal notice received from the third party",
      "Driving licence",
      "Vehicle registration certificate",
      "Insurance policy papers",
      "Duly filled claim form",
    ],
  },
];

const TAT_ROWS = [
  ["Appointment of surveyor", "Within 30 minutes – 24 hours of claim registration"],
  ["Submission of survey report", "Within 15 days of surveyor appointment"],
  ["Claim approval", "Within 7 days of the survey report"],
  ["Claim settlement", "Within 7 days of the final repair invoice"],
];

const PAYOUT_FACTORS = [
  {
    title: "Depreciation",
    desc: "Repaired parts attract depreciation: 50% on plastic parts, age-based rates on metal parts, none on glass. You bear the depreciated portion — unless you hold a zero-depreciation add-on, which pays the full amount.",
  },
  {
    title: "Excess (deductible)",
    desc: "Every policy carries a mandatory excess — the part of each claim you pay yourself. It applies to every claim, cashless or reimbursement.",
  },
  {
    title: "No Claim Bonus",
    desc: "Each claim-free year earns a growing premium discount. Filing any claim resets it to zero — so pay for minor scratches yourself and save the claims for losses that matter.",
  },
  {
    title: "Exclusions",
    desc: "Losses outside your policy's scope are denied outright. Check whether the damage is covered before filing — a rejected claim still costs you the paperwork.",
  },
  {
    title: "Add-ons",
    desc: "Roadside assistance, zero depreciation, return-to-invoice — if you bought them, use them. Check which add-ons apply before you settle for a smaller payout.",
  },
  {
    title: "Preferred garage",
    desc: "Cashless settlement only works at network garages. Find one near you before towing the car anywhere else.",
  },
];

const GUIDE_FAQS = [
  {
    q: "What happens if my car is declared a total loss?",
    a: "Based on the surveyor's recommendation, the claim is settled as repair, cash loss, or net of salvage — measured against your IDV. You provide a consent letter, original RC, policy, FIR where applicable, and the financer's NOC for financed vehicles. Keep the wreck safe until settlement: damage or theft of parts after the survey isn't covered. The policy is cancelled once the claim is paid.",
  },
  {
    q: "How is a theft claim settled?",
    a: "File the FIR immediately and notify your insurer with all original keys, the policy, and the RC. After the police issue a court-stamped non-traceable report, an investigator verifies the facts. You then transfer the RC to the insurer, hand over duplicate keys, an indemnity bond, and a subrogation letter — and the claim is paid at your vehicle's IDV.",
  },
  {
    q: "What if a third party sends me a legal notice?",
    a: "Forward it to your insurer immediately and never settle directly with the third party out of court. A lawyer is assigned after assessment, and the Motor Accident Claims Tribunal (MACT) with jurisdiction over the accident determines the compensation, which your insurer pays.",
  },
  {
    q: "Who is paid when the vehicle is financed?",
    a: "For total loss and theft settlements on financed vehicles, payment goes to the financer unless you provide an original No Objection Certificate (NOC). Any excess or deductible still applies per policy terms.",
  },
  {
    q: "Does submitting documents guarantee approval?",
    a: "No. Claims are verified against policy terms, conditions, and exclusions; insurers may request additional information. Misrepresentation or fraud leads to claim repudiation and can attract legal action. The policy wording always prevails over any guide.",
  },
];

export function GuidePage() {
  return (
    <div className="page page-guide">
      <div className="page-header">
        <div>
          <div className="eyebrow">Help &amp; Process</div>
          <h1>Claim Process Guide</h1>
          <p className="page-subtitle">
            Car insurance is mandatory under the Motor Vehicles Act, 1988 — and
            one mistake on the road can wipe out years of savings. Here is
            exactly how a motor claim works, from the first phone call to the
            money in your account.
          </p>
        </div>
        <Link to="/claims/new" className="btn btn-primary">
          File a claim
          <ArrowRight size={15} />
        </Link>
      </div>

      {/* When to file */}
      <h2 className="section-title">When should you file a claim?</h2>
      <div className="when-grid">
        {WHEN_TO_FILE.map((w) => {
          const Icon = w.icon;
          return (
            <div key={w.title} className="feature-card">
              <div className="feature-icon">
                <Icon size={24} />
              </div>
              <h3 className="feature-title">{w.title}</h3>
              <p className="feature-desc">{w.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Process steps */}
      <h2 className="section-title">The claim process, step by step</h2>
      <div className="card">
        <ol className="guide-steps">
          {PROCESS_STEPS.map((step, i) => (
            <li key={step.title} className="guide-step">
              <div className="guide-step-number">{i + 1}</div>
              <div>
                <div className="guide-step-title">{step.title}</div>
                <p className="guide-step-desc">{step.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Documents */}
      <h2 className="section-title">Documents you'll need</h2>
      <p className="muted" style={{ marginBottom: 18 }}>
        Every claim needs the basics — claim form, driving licence, RC, policy
        copy, and KYC documents (PAN/Aadhaar). Beyond those, each claim type
        has its own list:
      </p>
      <div className="doc-columns">
        {DOC_SETS.map((set) => (
          <div key={set.title} className="card doc-column">
            <h3>{set.title}</h3>
            <ul className="doc-list">
              {set.docs.map((doc) => (
                <li key={doc}>
                  <Check size={14} />
                  {doc}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Cashless vs reimbursement */}
      <h2 className="section-title">Cashless or reimbursement?</h2>
      <div className="compare-grid">
        <div className="card compare-card compare-recommended">
          <div className="compare-badge">Fastest route</div>
          <h3>Cashless claim</h3>
          <ul className="doc-list">
            <li>
              <Check size={14} />
              Repair at any network garage — the bill is settled directly with
              the garage
            </li>
            <li>
              <Check size={14} />
              No upfront payment; you pay only the deductibles and uncovered
              charges
            </li>
            <li>
              <Check size={14} />
              Best when you want a quick, hassle-free settlement
            </li>
          </ul>
        </div>
        <div className="card compare-card">
          <div className="compare-badge compare-badge-neutral">
            Full flexibility
          </div>
          <h3>Reimbursement claim</h3>
          <ul className="doc-list">
            <li>
              <Check size={14} />
              Repair at any garage you trust, network or not
            </li>
            <li>
              <Check size={14} />
              Pay out of pocket first, then claim it back with original
              invoices and payment receipts
            </li>
            <li>
              <Check size={14} />
              Original receipts are mandatory — keep everything
            </li>
          </ul>
        </div>
      </div>

      {/* TAT */}
      <h2 className="section-title">How long does it take?</h2>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Process stage</th>
              <th>Turnaround time (working days)</th>
            </tr>
          </thead>
          <tbody>
            {TAT_ROWS.map(([stage, tat]) => (
              <tr key={stage}>
                <td>{stage}</td>
                <td>{tat}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Payout factors */}
      <h2 className="section-title">Six things that change your payout</h2>
      <div className="when-grid payout-grid">
        {PAYOUT_FACTORS.map((f) => (
          <div key={f.title} className="card payout-card">
            <h3 className="feature-title">{f.title}</h3>
            <p className="feature-desc">{f.desc}</p>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <h2 className="section-title">Special cases</h2>
      {GUIDE_FAQS.map((f) => (
        <details key={f.q} className="faq-item">
          <summary>
            {f.q}
            <ChevronDown size={17} className="faq-chevron" />
          </summary>
          <p className="faq-answer">{f.a}</p>
        </details>
      ))}

      {/* Contact strip */}
      <div className="contact-strip">
        <div>
          <h2 className="contact-title">Need help right now?</h2>
          <p className="contact-sub">
            Claims can be registered 24×7 — by phone, on the website, or in
            the app.
          </p>
        </div>
        <div className="contact-channels">
          <div className="contact-channel">
            <span className="contact-label">Toll-free helpline</span>
            <span className="contact-value">1800-266-2255</span>
          </div>
          <div className="contact-channel">
            <span className="contact-label">24×7 roadside assistance</span>
            <span className="contact-value">1800-266-5858</span>
          </div>
          <Link to="/claims/new" className="btn btn-cta">
            <Banknote size={16} />
            Register a claim online
          </Link>
        </div>
      </div>

      <p className="muted small guide-disclaimer">
        This guide is for information only and does not override your policy
        wording — in any conflict, the policy document prevails. Submitting
        documents does not guarantee approval; all claims are verified against
        policy terms, conditions, and exclusions. Misrepresentation or fraud
        leads to repudiation and may attract legal action.
      </p>
    </div>
  );
}
