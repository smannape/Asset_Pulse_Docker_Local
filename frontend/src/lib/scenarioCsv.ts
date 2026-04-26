import { DEFAULT_INPUTS } from "../components/ScenarioForm";
import type { FiscalRegime, ScenarioInputs } from "./api";

export type ParsedScenarioRow = {
  scenario_name: string;
  asset_id_or_name: string;
  notes: string;
  inputs: ScenarioInputs;
  warnings: string[];
};

const VALID_REGIMES: ReadonlyArray<FiscalRegime> = [
  "us_royalty_tax",
  "noc_internal",
  "psc_cost_recovery",
  "technical_service_contract",
  "concession_tax_royalty",
];

// Columns where the CSV stores a percentage (e.g. 18.75 = 18.75%) but the
// API expects a fraction (0.1875). The mapper divides these by 100.
const PERCENT_FIELDS = new Set<keyof ScenarioInputs>([
  "annual_decline",
  "royalty_pct",
  "production_tax_pct",
  "discount_rate_annual",
  "water_cut_initial",
  "water_cut_final",
  "noc_government_share_pct",
  "noc_corp_tax_pct",
  "psc_royalty_pct",
  "psc_cost_oil_limit_pct",
  "psc_contractor_profit_share_pct",
  "psc_contractor_tax_pct",
  "psc_capex_uplift_pct",
  "tsc_payment_cap_pct",
  "tsc_contractor_tax_pct",
  "concession_royalty_pct",
  "concession_income_tax_pct",
]);

// Normalise CSV header to a canonical key: lowercase, strip whitespace and
// underscores, drop common unit suffixes that vary across spreadsheets.
function normaliseHeader(header: string): string {
  return header
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[_-]/g, "")
    .replace(/\(.*?\)/g, "");
}

// Map normalised CSV header → ScenarioInputs field name. Includes the column
// names from examples/asset_pulse_scenario_input_template.csv as well as the
// raw API field names produced by "Export scenario inputs".
const HEADER_ALIASES: Record<string, keyof ScenarioInputs> = {
  // Direct matches (raw API field names – keep first so the export round-trips).
  assetname: "asset_name",
  monthshorizon: "months_horizon",
  initialoilbopd: "initial_oil_bopd",
  initialgasmcfd: "initial_gas_mcfd",
  initialnglbpd: "initial_ngl_bpd",
  annualdecline: "annual_decline",
  declinemodel: "decline_model",
  bfactor: "b_factor",
  watercutinitial: "water_cut_initial",
  watercutfinal: "water_cut_final",
  oilprice: "oil_price",
  gasprice: "gas_price",
  nglprice: "ngl_price",
  royaltypct: "royalty_pct",
  productiontaxpct: "production_tax_pct",
  transportperboe: "transport_per_boe",
  processingperboe: "processing_per_boe",
  fixedopexpermonth: "fixed_opex_per_month",
  oilvarperbbl: "oil_var_per_bbl",
  gasvarpermcf: "gas_var_per_mcf",
  watervarperbbl: "water_var_per_bbl",
  developmentcapex: "development_capex",
  sustainingcapexpermonth: "sustaining_capex_per_month",
  abandonmentcost: "abandonment_cost",
  discountrateannual: "discount_rate_annual",
  capexmultiplier: "capex_multiplier",
  opexmultiplier: "opex_multiplier",
  applyeconomiclimit: "apply_economic_limit",
  fiscalregime: "fiscal_regime",
  nocgovernmentsharepct: "noc_government_share_pct",
  noccorptaxpct: "noc_corp_tax_pct",
  pscroyaltypct: "psc_royalty_pct",
  psccostoillimitpct: "psc_cost_oil_limit_pct",
  psccontractorprofitsharepct: "psc_contractor_profit_share_pct",
  psccontractortaxpct: "psc_contractor_tax_pct",
  psccapexupliftpct: "psc_capex_uplift_pct",
  tscpaymentcappct: "tsc_payment_cap_pct",
  tscremunerationperboe: "tsc_remuneration_per_boe",
  tsccontractortaxpct: "tsc_contractor_tax_pct",
  concessionroyaltypct: "concession_royalty_pct",
  concessionincometaxpct: "concession_income_tax_pct",
  concessionroyaltyprogressive: "concession_royalty_progressive",

  // Template-style aliases.
  oilpriceusdbbl: "oil_price",
  gaspriceusdmcf: "gas_price",
  nglpriceusdbbl: "ngl_price",
  declinerateannualpct: "annual_decline",
  months: "months_horizon",
  royaltyratepct: "royalty_pct",
  severancetaxratepct: "production_tax_pct",
  discountratepct: "discount_rate_annual",
  capextotalusd: "development_capex",
  fixedopexusdmonth: "fixed_opex_per_month",
  variableopexusdboe: "oil_var_per_bbl",
  waterhandlingusdbbl: "water_var_per_bbl",
  watercutpct: "water_cut_initial",
  pscroyaltyratepct: "psc_royalty_pct",
  psccostrecoveryceilingpct: "psc_cost_oil_limit_pct",
  psccontractorprofitoilsharepct: "psc_contractor_profit_share_pct",
  contractortaxratepct: "psc_contractor_tax_pct",
  capexupliftpct: "psc_capex_uplift_pct",
  tscfeeusdboe: "tsc_remuneration_per_boe",
  concessionroyaltyratepct: "concession_royalty_pct",
  concessionincometaxratepct: "concession_income_tax_pct",
};

function parseBool(raw: string): boolean | null {
  const v = raw.trim().toLowerCase();
  if (v === "true" || v === "1" || v === "yes" || v === "y") return true;
  if (v === "false" || v === "0" || v === "no" || v === "n") return false;
  return null;
}

function parseNumber(raw: string): number | null {
  const cleaned = raw.replace(/[$,_\s]/g, "").replace(/%$/, "");
  if (cleaned === "") return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function mapCsvRowToInputs(
  row: Record<string, string>,
  base: ScenarioInputs = DEFAULT_INPUTS,
): ParsedScenarioRow {
  const inputs: ScenarioInputs = { ...base };
  const warnings: string[] = [];

  let scenarioName = "";
  let assetIdOrName = "";
  let notes = "";

  for (const [rawHeader, rawValue] of Object.entries(row)) {
    const value = rawValue.trim();
    const norm = normaliseHeader(rawHeader);

    if (norm === "scenarioname") {
      scenarioName = value;
      continue;
    }
    if (norm === "assetidorname") {
      assetIdOrName = value;
      continue;
    }
    if (norm === "notes") {
      notes = value;
      continue;
    }

    const field = HEADER_ALIASES[norm];
    if (!field) continue;
    if (value === "") continue;

    if (field === "asset_name" || field === "decline_model") {
      if (field === "decline_model") {
        const dm = value.toLowerCase();
        if (dm === "exponential" || dm === "hyperbolic" || dm === "harmonic") {
          inputs.decline_model = dm;
        } else {
          warnings.push(`Unknown decline_model "${value}" — kept default.`);
        }
      } else {
        inputs.asset_name = value;
      }
      continue;
    }

    if (field === "fiscal_regime") {
      if ((VALID_REGIMES as readonly string[]).includes(value)) {
        inputs.fiscal_regime = value as FiscalRegime;
      } else {
        warnings.push(`Unknown fiscal_regime "${value}" — kept default.`);
      }
      continue;
    }

    if (field === "apply_economic_limit" || field === "concession_royalty_progressive") {
      const b = parseBool(value);
      if (b === null) {
        warnings.push(`Invalid boolean for ${field}: "${value}".`);
      } else {
        (inputs as unknown as Record<string, boolean>)[field] = b;
      }
      continue;
    }

    const n = parseNumber(value);
    if (n === null) {
      warnings.push(`Non-numeric value for ${field}: "${value}".`);
      continue;
    }

    const final = PERCENT_FIELDS.has(field) ? n / 100 : n;
    (inputs as unknown as Record<string, number>)[field] = final;
  }

  // Prefer asset_id_or_name as the display label if asset_name wasn't set.
  if (assetIdOrName && (!row["asset_name"] || row["asset_name"].trim() === "")) {
    inputs.asset_name = assetIdOrName;
  }

  return {
    scenario_name: scenarioName,
    asset_id_or_name: assetIdOrName,
    notes,
    inputs,
    warnings,
  };
}
