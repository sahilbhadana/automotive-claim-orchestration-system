import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createClaim } from "../api/endpoints";
import type { ClaimType } from "../api/types";

const CLAIM_TYPE_OPTIONS: { value: ClaimType; label: string; hint: string }[] = [
  {
    value: "ACCIDENT",
    label: "Accident / Collision",
    hint: "Damage to your own vehicle from an accident.",
  },
  {
    value: "THEFT",
    label: "Theft",
    hint: "Vehicle stolen — FIR and IDV are mandatory; settles at IDV.",
  },
  {
    value: "THIRD_PARTY",
    label: "Third-party liability",
    hint: "Your vehicle harmed someone else or their property — FIR mandatory; decided via legal review (MACT).",
  },
  {
    value: "NATURAL_DISASTER",
    label: "Natural / man-made disaster",
    hint: "Flood, fire, storm, earthquake, or vandalism damage.",
  },
];

export function NewClaimPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    policy_number: "",
    vehicle_number: "",
    incident_date: "",
    incident_city: "",
    claim_amount: "",
    description: "",
    claim_type: "ACCIDENT" as ClaimType,
    fir_number: "",
    idv: "",
    driving_license_number: "",
    license_expiry_date: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (key: keyof typeof form) => (value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const firRequired =
    form.claim_type === "THEFT" || form.claim_type === "THIRD_PARTY";
  const idvRequired = form.claim_type === "THEFT";
  // The driver's licence is only relevant when a driver was operating
  // the vehicle (accident, third-party); a parked car has no driver.
  const licenseRequired =
    form.claim_type === "ACCIDENT" || form.claim_type === "THIRD_PARTY";
  const selectedType = CLAIM_TYPE_OPTIONS.find(
    (o) => o.value === form.claim_type,
  );

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const claim = await createClaim({
        policy_number: form.policy_number,
        vehicle_number: form.vehicle_number,
        incident_date: form.incident_date,
        incident_city: form.incident_city,
        claim_amount: Number(form.claim_amount),
        description: form.description,
        claim_type: form.claim_type,
        fir_number: form.fir_number || null,
        idv: form.idv ? Number(form.idv) : null,
        driving_license_number: form.driving_license_number || null,
        license_expiry_date: form.license_expiry_date || null,
      });
      navigate(`/claims/${claim.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create claim");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <div className="eyebrow">Workspace</div>
          <h1>File a New Claim</h1>
          <p className="page-subtitle">
            First notice of loss. Once submitted, the claim enters document
            verification and your adjuster team is notified.
          </p>
          <p className="have-ready">
            Have ready: your policy number, vehicle registration, accident
            photos, and the FIR copy for theft, third-party, or major damage.{" "}
            <Link to="/guide">See the full document list</Link>
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card form-card">
        {error && <div className="alert alert-error">{error}</div>}

        <label className="field">
          <span>What happened?</span>
          <select
            value={form.claim_type}
            onChange={(e) => update("claim_type")(e.target.value)}
          >
            {CLAIM_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {selectedType && <small className="muted">{selectedType.hint}</small>}
        </label>

        <div className="form-row">
          <label className="field">
            <span>Policy number</span>
            <input
              value={form.policy_number}
              onChange={(e) => update("policy_number")(e.target.value)}
              required
              minLength={3}
              placeholder="POL-2026-001234"
            />
          </label>
          <label className="field">
            <span>Vehicle number</span>
            <input
              value={form.vehicle_number}
              onChange={(e) => update("vehicle_number")(e.target.value)}
              required
              minLength={3}
              placeholder="GJ01AA9999"
            />
          </label>
        </div>

        <div className="form-row">
          <label className="field">
            <span>Incident date</span>
            <input
              type="date"
              value={form.incident_date}
              onChange={(e) => update("incident_date")(e.target.value)}
              required
              max={new Date().toISOString().split("T")[0]}
            />
          </label>
          <label className="field">
            <span>Incident city</span>
            <input
              value={form.incident_city}
              onChange={(e) => update("incident_city")(e.target.value)}
              required
              minLength={2}
              placeholder="Ahmedabad"
            />
          </label>
        </div>

        <div className="form-row">
          <label className="field">
            <span>Claim amount (₹)</span>
            <input
              type="number"
              value={form.claim_amount}
              onChange={(e) => update("claim_amount")(e.target.value)}
              required
              min={1}
              step="0.01"
              placeholder="75000"
            />
          </label>
          <label className="field">
            <span>
              Insured Declared Value (₹){idvRequired ? "" : " — optional"}
            </span>
            <input
              type="number"
              value={form.idv}
              onChange={(e) => update("idv")(e.target.value)}
              required={idvRequired}
              min={1}
              step="0.01"
              placeholder="450000"
            />
          </label>
        </div>

        <label className="field">
          <span>FIR number{firRequired ? " (mandatory)" : " — optional"}</span>
          <input
            value={form.fir_number}
            onChange={(e) => update("fir_number")(e.target.value)}
            required={firRequired}
            minLength={firRequired ? 3 : undefined}
            placeholder="FIR-2026-04521"
          />
          {firRequired && (
            <small className="muted">
              An FIR filed at the nearest police station is mandatory for{" "}
              {form.claim_type === "THEFT" ? "theft" : "third-party"} claims.
            </small>
          )}
        </label>

        {licenseRequired && (
          <div className="form-row">
            <label className="field">
              <span>Driving licence number (mandatory)</span>
              <input
                value={form.driving_license_number}
                onChange={(e) =>
                  update("driving_license_number")(e.target.value)
                }
                required={licenseRequired}
                minLength={5}
                placeholder="MH1420110012345"
              />
            </label>
            <label className="field">
              <span>Licence expiry date (mandatory)</span>
              <input
                type="date"
                value={form.license_expiry_date}
                onChange={(e) => update("license_expiry_date")(e.target.value)}
                required={licenseRequired}
              />
              <small className="muted">
                The licence must have been valid on the incident date, or the
                claim will be rejected at policy validation.
              </small>
            </label>
          </div>
        )}

        <label className="field">
          <span>Description of incident</span>
          <textarea
            value={form.description}
            onChange={(e) => update("description")(e.target.value)}
            required
            minLength={10}
            maxLength={1000}
            rows={4}
            placeholder="Describe what happened (minimum 10 characters)…"
          />
        </label>

        <div className="form-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => navigate("/claims")}
          >
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Submitting…" : "Submit Claim"}
          </button>
        </div>
      </form>
    </div>
  );
}
