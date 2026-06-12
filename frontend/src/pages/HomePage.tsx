import { Link } from "react-router-dom";
import {
  ArrowRight,
  Banknote,
  ChevronDown,
  GitBranch,
  RefreshCcw,
  ScrollText,
  Siren,
  UsersRound,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const STATS = [
  { value: "12,400+", label: "claims processed" },
  { value: "₹38 Cr", label: "settled to date" },
  { value: "4.8 days", label: "median settlement time" },
  { value: "99.2%", label: "payout success rate" },
];

const STEPS = [
  {
    number: "01",
    title: "File the claim",
    desc: "Policy, vehicle, and incident details captured in under two minutes. The workflow starts the moment you submit.",
  },
  {
    number: "02",
    title: "Verify & score",
    desc: "Documents are checked, the policy validated, and every claim passes through six families of fraud rules before a human ever approves it.",
  },
  {
    number: "03",
    title: "Assign & estimate",
    desc: "The best adjuster is matched by city, expertise, and current workload. Repair quotes flow in from partner garages.",
  },
  {
    number: "04",
    title: "Approve & pay",
    desc: "Supervisors sign off, and payouts run with automatic retries. Failed transfers never vanish — they wait in a recovery queue.",
  },
];

const FEATURES = [
  {
    icon: GitBranch,
    title: "Enforced workflow",
    desc: "Nine stages from first notice of loss to payout. Skipped steps are rejected at the API — process is policy, not convention.",
  },
  {
    icon: Siren,
    title: "Fraud scoring",
    desc: "Duplicate vehicles, repeat incidents, inflated estimates, and flagged garages scored on every claim, before approval.",
  },
  {
    icon: Banknote,
    title: "Resilient payouts",
    desc: "Bank transfers retry with exponential backoff — 30s, 60s, 120s — and exhausted retries land in a dead-letter queue.",
  },
  {
    icon: ScrollText,
    title: "Complete audit trail",
    desc: "Every state change, document upload, and payout attempt is recorded with actor and timestamp. Nothing is off the record.",
  },
  {
    icon: UsersRound,
    title: "Role-based access",
    desc: "Customers file and track. Adjusters assess. Supervisors approve. Admins operate. Each role sees exactly what it needs.",
  },
  {
    icon: RefreshCcw,
    title: "Live operations",
    desc: "Prometheus metrics, health probes, and a recovery console give operators a real-time view of the whole claim engine.",
  },
];

const ARTICLES = [
  {
    category: "Fraud",
    title: "How rule-based scoring stops claim leakage before payout",
    excerpt:
      "Most fraud is caught after the money moves. We score duplicate vehicles, repeat incident patterns, and garage history while the claim is still in review — here's the rule set.",
    date: "May 28, 2026",
    readTime: "6 min read",
    tint: "moss",
  },
  {
    category: "Engineering",
    title: "Designing payout retries that never lose money",
    excerpt:
      "A failed bank transfer is not an error message — it's a liability. Why we built exponential backoff with a dead-letter queue instead of fire-and-forget background jobs.",
    date: "May 14, 2026",
    readTime: "8 min read",
    tint: "clay",
  },
  {
    category: "Operations",
    title: "What a nine-stage claim workflow looks like in practice",
    excerpt:
      "From first notice of loss to settled payout: where claims stall, which transitions get rejected most, and how adjuster workload balancing changed our cycle time.",
    date: "April 30, 2026",
    readTime: "5 min read",
    tint: "stone",
  },
];

const TESTIMONIALS = [
  {
    quote:
      "We went from spreadsheets and email chains to a single queue. Our adjusters stopped asking 'where is this claim?' because the answer is always on screen.",
    name: "Priya Raghavan",
    role: "Claims Operations Lead, Meridian General",
  },
  {
    quote:
      "The fraud scoring paid for the platform in the first quarter. Two garage rings we'd have paid out without blinking got flagged on day one.",
    name: "Arjun Mehta",
    role: "Head of Underwriting, Sahyadri Insurance",
  },
  {
    quote:
      "Payouts used to fail silently and surface as customer complaints. Now they retry themselves, and the rare stragglers sit in a queue my team clears before lunch.",
    name: "Kavitha Nair",
    role: "Settlement Manager, Coastal Mutual",
  },
];

const FAQS = [
  {
    q: "Can a claim skip stages if a supervisor approves it?",
    a: "No. The workflow is a state machine enforced at the API level — a claim in document verification cannot jump to approval, regardless of who asks. This is what makes the audit trail trustworthy.",
  },
  {
    q: "What happens when a payout fails?",
    a: "The transfer retries automatically with exponential backoff: 30 seconds, then 60, then 120. If all retries are exhausted, the settlement is parked in the dead-letter queue where an operator can requeue, reschedule, or dismiss it with full error context. No payment is ever silently dropped.",
  },
  {
    q: "How does adjuster assignment work?",
    a: "When a claim reaches the assignment stage, the system ranks active adjusters by city match, expertise tier for the claim amount, and current open workload — then assigns the best fit. Assignments are logged like every other action.",
  },
  {
    q: "Who can see what?",
    a: "Customers see their claims and documents. Adjusters add settlements and fraud analyses. Supervisors approve claims and initiate payouts. Administrators get the recovery queue and live system health. Permissions are enforced server-side on every request.",
  },
];

export function HomePage() {
  const { user } = useAuth();

  return (
    <div className="page home">
      {/* ---- Hero ---- */}
      <section className="home-hero">
        <div className="eyebrow">Claims, settled properly</div>
        <h1 className="home-title">
          The claim engine that treats
          <br />
          <span className="accent-text">process as a promise.</span>
        </h1>
        <p className="home-lede">
          ClaimFlow runs the full automotive claim lifecycle — intake, document
          verification, fraud analysis, adjuster assignment, and payout — on
          one audited workflow. Welcome back
          {user ? `, ${user.full_name.split(" ")[0]}` : ""}.
        </p>
        <div className="action-row">
          <Link to="/claims/new" className="btn btn-primary">
            File a claim
            <ArrowRight size={15} />
          </Link>
          <Link to="/claims" className="btn btn-secondary">
            View my claims
          </Link>
        </div>
      </section>

      {/* ---- Stats band ---- */}
      <section className="home-stats">
        {STATS.map((s) => (
          <div key={s.label} className="home-stat">
            <div className="home-stat-value">{s.value}</div>
            <div className="home-stat-label">{s.label}</div>
          </div>
        ))}
      </section>

      {/* ---- How it works ---- */}
      <section className="home-section">
        <div className="home-section-head">
          <div className="eyebrow">How it works</div>
          <h2 className="home-h2">Four moves, start to settled</h2>
        </div>
        <div className="home-steps">
          {STEPS.map((step) => (
            <div key={step.number} className="home-step">
              <div className="home-step-number">{step.number}</div>
              <h3 className="home-step-title">{step.title}</h3>
              <p className="home-step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---- Features ---- */}
      <section className="home-section">
        <div className="home-section-head">
          <div className="eyebrow">What's inside</div>
          <h2 className="home-h2">Built for the unglamorous parts</h2>
          <p className="home-section-sub">
            The hard problems in claims aren't forms — they're fraud, failed
            payments, and finding out what happened three weeks ago.
          </p>
        </div>
        <div className="feature-grid">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="feature-card">
                <div className="feature-icon">
                  <Icon size={26} />
                </div>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-desc">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ---- Articles ---- */}
      <section className="home-section">
        <div className="home-section-head">
          <div className="eyebrow">From the field notes</div>
          <h2 className="home-h2">Reading for claims people</h2>
        </div>
        <div className="article-grid">
          {ARTICLES.map((a) => (
            <article key={a.title} className="article-card">
              <div className={`article-banner article-banner-${a.tint}`}>
                <span className="article-chip">{a.category}</span>
              </div>
              <div className="article-body">
                <h3 className="article-title">{a.title}</h3>
                <p className="article-excerpt">{a.excerpt}</p>
                <div className="article-meta">
                  <span>{a.date}</span>
                  <span>·</span>
                  <span>{a.readTime}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ---- Testimonials ---- */}
      <section className="home-section">
        <div className="home-section-head">
          <div className="eyebrow">In their words</div>
          <h2 className="home-h2">Teams that settled in</h2>
        </div>
        <div className="testimonial-grid">
          {TESTIMONIALS.map((t) => (
            <figure key={t.name} className="testimonial-card">
              <blockquote className="testimonial-quote">
                &ldquo;{t.quote}&rdquo;
              </blockquote>
              <figcaption>
                <div className="testimonial-name">{t.name}</div>
                <div className="testimonial-role">{t.role}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      {/* ---- FAQ ---- */}
      <section className="home-section home-faq">
        <div className="home-section-head">
          <div className="eyebrow">Common questions</div>
          <h2 className="home-h2">Asked before, answered properly</h2>
        </div>
        {FAQS.map((f) => (
          <details key={f.q} className="faq-item">
            <summary>
              {f.q}
              <ChevronDown size={17} className="faq-chevron" />
            </summary>
            <p className="faq-answer">{f.a}</p>
          </details>
        ))}
        <p className="faq-more">
          Want the full picture — documents, timelines, theft and third-party
          cases? <Link to="/guide">Read the claim process guide</Link>
        </p>
      </section>

      {/* ---- Final CTA ---- */}
      <section className="home-cta">
        <h2 className="home-cta-title">Something happen to the car?</h2>
        <p className="home-cta-sub">
          File the claim now — the workflow takes it from here.
        </p>
        <Link to="/claims/new" className="btn btn-cta">
          Start a new claim
          <ArrowRight size={16} />
        </Link>
      </section>

      {/* ---- Footer ---- */}
      <footer className="home-footer">
        <div className="home-footer-brand">
          <span className="brand-name">ClaimFlow</span>
          <p className="muted small">
            Automotive claim orchestration — intake to payout, audited end to
            end.
          </p>
        </div>
        <div className="home-footer-links">
          <Link to="/claims">Claims</Link>
          <Link to="/claims/new">File a claim</Link>
          <Link to="/guide">Claim guide</Link>
          {(user?.role === "adjuster" ||
            user?.role === "supervisor" ||
            user?.role === "admin") && (
            <Link to="/settlements">Settlements</Link>
          )}
          {user?.role === "admin" && <Link to="/admin/system">Status</Link>}
        </div>
        <div className="muted small">
          © {new Date().getFullYear()} ClaimFlow. Crafted with patience.
        </div>
      </footer>
    </div>
  );
}
