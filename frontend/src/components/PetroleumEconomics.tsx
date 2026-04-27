import type { ReactNode } from "react";

// Petroleum Economics flow-chart explainer.
// Pure CSS/SVG visuals, no external chart deps — keeps the bundle thin and
// stays consistent with the terminal/Palantir aesthetic.

type Block = { title: string; body: string };

function FlowRow({ blocks }: { blocks: Block[] }) {
  return (
    <div className="pe-flow-row">
      {blocks.map((b, i) => (
        <div className="pe-flow-step" key={`${i}-${b.title}`}>
          <div className="pe-block">
            <div className="pe-block-title">{b.title}</div>
            <div className="pe-block-body">{b.body}</div>
          </div>
          {i < blocks.length - 1 && (
            <div className="pe-arrow" aria-hidden="true">
              ▶
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function FlowGrid({ blocks }: { blocks: Block[] }) {
  return (
    <div className="pe-flow-grid">
      {blocks.map((b, i) => (
        <div className="pe-block grid" key={`${i}-${b.title}`}>
          <div className="pe-block-title">{b.title}</div>
          <div className="pe-block-body">{b.body}</div>
        </div>
      ))}
    </div>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="pe-section">
      <div className="pe-section-head">
        <h3>{title}</h3>
        {subtitle && <span className="muted">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

const WORKFLOW: Block[] = [
  {
    title: "Inputs",
    body: "Volumes, prices, decline, water cut, fluid mix, horizon.",
  },
  {
    title: "Fiscal regime",
    body: "Royalty/tax · PSC · TSC · NOC · Concession.",
  },
  {
    title: "Production forecast",
    body: "Decline curve (exp / hyp / harm), water cut ramp, EUR.",
  },
  {
    title: "Revenue",
    body: "Oil + gas + NGL × price deck − differentials.",
  },
  { title: "OPEX", body: "Fixed LOE + variable + water + transport." },
  {
    title: "CAPEX & cost recovery",
    body: "Dev CAPEX, sustaining, ARO, uplift, cost-oil ceilings.",
  },
  {
    title: "Taxes / royalty / share",
    body: "Royalties, prod tax, income tax, gov profit share.",
  },
  {
    title: "NPV / breakeven / payback",
    body: "Discounted cash flow → KPIs.",
  },
  { title: "Decision", body: "Drill · keep online · choke · shut-in · defer." },
];

const CAPEX: Block[] = [
  {
    title: "Drilling & completion",
    body: "Day-rate × spread, casing, cementing, frac stages, wireline. Largest single line item — often 60–75% of well CAPEX.",
  },
  {
    title: "Surface facilities",
    body: "Wellhead, separator, treater, pumps, tank battery, instrumentation.",
  },
  {
    title: "Tie-in / pipeline / gathering",
    body: "Flowlines, ROW, hydrostatic test, trunkline metering, custody transfer.",
  },
  {
    title: "Artificial lift",
    body: "ESP, rod-pump, gas-lift compression, downhole pumps and VFDs.",
  },
  {
    title: "Workover / recompletion",
    body: "Plug-and-perf, refracs, scale/sand cleanout, intervention.",
  },
  {
    title: "Abandonment / ARO",
    body: "P&A liability, surface restoration. Capitalized in the asset retirement reserve.",
  },
  {
    title: "Contingency & escalation",
    body: "10–20% contingency on field cost · supply-chain inflation factor.",
  },
];

const OPEX: Block[] = [
  {
    title: "Fixed LOE",
    body: "Field labour, supervision, surface integrity, well checks. Independent of throughput.",
  },
  {
    title: "Variable LOE / BOE",
    body: "Per-bbl, per-mcf, per-bbl-water variable cost — scales with rate.",
  },
  {
    title: "Water handling",
    body: "Lift, separation, treatment, SWD or trucking. Dominates mature field cost.",
  },
  {
    title: "Energy / power",
    body: "Diesel, electricity, gas-lift compression, fuel gas allocation.",
  },
  {
    title: "Chemicals",
    body: "Demulsifiers, scale and corrosion inhibitors, biocide, methanol.",
  },
  {
    title: "Maintenance & workover",
    body: "Pump changes, rod jobs, surface MROs. Often blended into OPEX/BOE in budget views.",
  },
  {
    title: "Logistics",
    body: "Trucking, marine, helicopter, base camp — major in remote/offshore.",
  },
  {
    title: "G&A / field supervision",
    body: "Field office, HSE, regulatory reporting, allocated corporate G&A.",
  },
  {
    title: "Downtime",
    body: "Lost-revenue exposure during planned/unplanned shut-ins. Modeled via Events.",
  },
];

type Region = {
  name: string;
  regimes: string;
  signature: string;
  notes: string[];
};

const REGIONS: Region[] = [
  {
    name: "Middle East",
    regimes: "Concession (KSA, Kuwait, UAE) · TSC (Iraq, Iran) · PSC (Egypt, Oman selected)",
    signature: "NOC strategic constraints · subsidised energy · low lifting cost",
    notes: [
      "Progressive royalty (e.g. KSA 15%/45%/80% above $70/$100).",
      "TSC remuneration $/BOE with cost-recovery cap, not equity barrels.",
      "Heavy NOC alignment: production caps, OPEC+ quotas, gas-flaring rules.",
    ],
  },
  {
    name: "North Africa",
    regimes: "PSC / EPSA (Egypt, Libya) · concession (Algeria with Sonatrach)",
    signature: "Cost-oil ceilings, security premium, FX/local content",
    notes: [
      "Cost-oil limit typically 30–50% of revenue; uplift 5–20%.",
      "Local content quotas, payment-in-kind for some service tiers.",
      "Security/insurance load can move OPEX/BOE materially.",
    ],
  },
  {
    name: "South America",
    regimes: "Concession (Argentina) · PSC (Brazil pre-salt) · TSC-style (Mexico CNH)",
    signature: "FX volatility, basin differentials, deep-water facilities CAPEX",
    notes: [
      "Brazil pre-salt: high CAPEX, FPSO cost, gov't profit oil tiers.",
      "Argentina: peso convertibility risk, export taxes, Vaca Muerta inflation.",
      "Heavy-oil belts (Venezuela/Ecuador) carry diluent cost & quality discounts.",
    ],
  },
  {
    name: "North America",
    regimes: "Royalty/tax (US private + federal) · royalty/tax (Canada Crown)",
    signature: "Liquid market, basis differentials, service-cost cyclicality",
    notes: [
      "Royalty 12.5–25% private; severance/production tax 2–8%.",
      "Basis differentials matter (WTI Midland, WCS heavy, AECO gas).",
      "ARO / state P&A bonds rising — model the back-end ARO line.",
    ],
  },
  {
    name: "Asia",
    regimes: "PSC (Indonesia, Malaysia, Vietnam) · concession (Australia)",
    signature: "Cost-recovery PSCs, gas-monetisation constraints",
    notes: [
      "Indonesia gross-split PSC removes cost recovery — share is rate-sensitive.",
      "Australia PRRT: ring-fenced profit-tax with uplift on carry-forward.",
      "Gas projects gated by LNG offtake & domestic supply obligations.",
    ],
  },
  {
    name: "Europe",
    regimes: "Concession + special tax (UK, Norway) · royalty/tax (NL, DK)",
    signature: "Mature basins, decommissioning liability, carbon cost",
    notes: [
      "UK: 30% ring-fence corp tax + 10% supplementary + EPL surcharge.",
      "Norway: 22% corp + 56% special tax with ~71.8% effective marginal.",
      "ETS / carbon price now a real OPEX line ($60–90/tCO₂ recent range).",
    ],
  },
];

export function PetroleumEconomics() {
  return (
    <div className="pe-root">
      <div className="panel">
        <header>
          <h2>Why this section</h2>
          <span className="meta muted">read before running scenarios</span>
        </header>
        <div className="body">
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55 }}>
            Petroleum economics ties together <b>volumes, prices, costs and
            fiscal terms</b> into a single discounted-cash-flow view. The flow
            charts below show the calculation chain Asset Pulse uses, and the
            key inputs you should sanity-check before trusting an NPV. Pick a
            region card to see the dominant regime and what tends to move the
            answer in that basin.
          </p>
        </div>
      </div>

      <div className="panel">
        <header>
          <h2>1 · Scenario economics workflow</h2>
          <span className="meta muted">inputs → fiscal → forecast → DCF → decision</span>
        </header>
        <div className="body">
          <FlowRow blocks={WORKFLOW} />
        </div>
      </div>

      <div className="panel">
        <header>
          <h2>2 · Key CAPEX inputs</h2>
          <span className="meta muted">field-development capital build-up</span>
        </header>
        <div className="body">
          <Section
            title="What to capture"
            subtitle="Drives breakeven and payback most directly"
          >
            <FlowGrid blocks={CAPEX} />
          </Section>
        </div>
      </div>

      <div className="panel">
        <header>
          <h2>3 · Key OPEX inputs</h2>
          <span className="meta muted">monthly operating cost structure</span>
        </header>
        <div className="body">
          <Section
            title="What to capture"
            subtitle="Determines economic limit and netback / BOE"
          >
            <FlowGrid blocks={OPEX} />
          </Section>
        </div>
      </div>

      <div className="panel">
        <header>
          <h2>4 · Regional variables</h2>
          <span className="meta muted">how geography rewrites the inputs</span>
        </header>
        <div className="body">
          <div className="pe-region-grid">
            {REGIONS.map((r) => (
              <div key={r.name} className="pe-region-card">
                <div className="pe-region-head">
                  <span className="pe-region-name">{r.name}</span>
                  <span className="pe-region-regimes">{r.regimes}</span>
                </div>
                <div className="pe-region-sig">{r.signature}</div>
                <ul className="pe-region-notes">
                  {r.notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="panel">
        <header>
          <h2>5 · Run-it checklist</h2>
          <span className="meta muted">before saving a scenario</span>
        </header>
        <div className="body">
          <ol className="pe-check">
            <li>Have you picked the right fiscal regime for the basin?</li>
            <li>Are CAPEX inputs split into dev / sustaining / ARO?</li>
            <li>Does OPEX include water handling and energy?</li>
            <li>Is the price deck consistent with the basis differential?</li>
            <li>Does the discount rate reflect cost of capital and country risk?</li>
            <li>Have you stress-tested via Tornado and Monte Carlo?</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
