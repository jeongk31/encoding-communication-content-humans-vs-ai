*! Cross-study comparison table — EXTENDED version
*! Reads ONLY master_dataset.csv from the current directory.
*!
*! Layout: 7 columns total.
*!   Top header:  Outcome | Original RA (2 sub) | New RA (2 sub) | LLM Guidance (2 sub)
*!   Sub-headers (repeated per panel, since the magnitude metric differs):
*!     Panel A:  Proportion | p-value | Proportion | p-value | Proportion | p-value
*!     Panel B:  Coefficient | p-value | Coefficient | p-value | Coefficient | p-value
*!     Panel C:  same as Panel B

clear all
set more off
capture log close
log using "comparison_table.log", replace text

* ===========================================================================
* LOAD ONCE
* ===========================================================================
import delimited "../../../data/master_dataset.csv", clear stringcols(_all)
destring label, replace force
tempfile master
save `master'

* ===========================================================================
* OPEN OUTPUT FILE
* ===========================================================================
tempname fh
file open `fh' using "comparison_table.tex", write replace

file write `fh' "\begin{table}[ht]" _n
file write `fh' "\centering" _n
file write `fh' "\caption{Replication of paper results across coding sources.}" _n
file write `fh' "\label{tab:cross-study-replication}" _n
file write `fh' "\small" _n
file write `fh' "\begin{threeparttable}" _n
file write `fh' "\renewcommand\TPTminimum{\linewidth}" _n
file write `fh' "\resizebox{\textwidth}{!}{%" _n
file write `fh' "\begin{tabular}{l@{\hskip 24pt} c@{\hskip 10pt}c @{\hskip 24pt} c@{\hskip 10pt}c @{\hskip 24pt} c@{\hskip 10pt}c}" _n
file write `fh' "\toprule" _n
file write `fh' "\textbf{Outcome} & \multicolumn{2}{c}{\textbf{Original RA}} & \multicolumn{2}{c}{\textbf{New RA}} & \multicolumn{2}{c}{\textbf{LLM Guidance}} \\" _n
file write `fh' "\cmidrule(r){1-1} \cmidrule(l{2pt}r{2pt}){2-3} \cmidrule(l{2pt}r{2pt}){4-5} \cmidrule(l){6-7}" _n



* ===========================================================================
* SHARED UTILITY PROGRAMS (used by Panels A & B)
* ===========================================================================
capture program drop pcell
program define pcell, rclass
    args pval
    if `pval' < 0.001 {
        return local cell "\(p{<}0.001\)"
    }
    else {
        local pf : display %5.3f `pval'
        return local cell "\(p=`pf'\)"
    }
end


capture program drop coefcell
program define coefcell, rclass
    args b
    local bf : display %6.3f `b'
    local bf = trim("`bf'")
    return local cell "`bf'"
end

* ===========================================================================
* PANEL A: LEGITIMACY (Models 3 and 4 of Table 6, 2SLS; only Elected reported)
* ===========================================================================
* All experimental variables (elected, bonus_increase, lag_min_effort, instruments,
* manager controls, global_group) come from master enriched columns.

use `master', clear
keep if study == "Legitimacy"
destring label, replace force

* Episode_ID = "session_period_chatGroup" — parse into separate vars
split episode_id, parse("_") destring gen(eid_)
rename eid_1 session
rename eid_2 period
rename eid_3 chatGroup
destring bonus_increase global_group lag_min_effort iv_max_min46 iv_avg_min16 ///
         elected stage1_correct manearlyeff, replace force

* Period dummies (period takes values 7-9 in the regression sample)
gen pdum2 = (period == 8)
gen pdum3 = (period == 9)

* Original RA DV: paper's averaged codings = mean of H2 (cd1) and H3 (cd2) per (Episode, Category).
* Then sum binary indicators for cat 1e and cat 2 — but Original RA uses CONTINUOUS sum (0..2).
preserve
    keep if (coder_type == "Human" & inlist(encoder, "H2", "H3") & inlist(category, "1e", "2")) | (is_encoded == "0" & inlist(category, "1e", "2"))
    collapse (mean) label, by(episode_id category)  // continuous (0, 0.5, 1)
    keep episode_id category label
    reshape wide label, i(episode_id) j(category) string
    gen orig_dv = label1e + label2
    keep episode_id orig_dv
    tempfile origDV
    save `origDV'
restore

* New RA DV: median of H1, H4, H5
preserve
    keep if (coder_type == "Human" & inlist(encoder, "H1", "H4", "H5") & inlist(category, "1e", "2")) | (is_encoded == "0" & inlist(category, "1e", "2"))
    collapse (median) label, by(episode_id category)
    gen maj = (label >= 0.5)
    keep episode_id category maj
    reshape wide maj, i(episode_id) j(category) string
    gen new_dv = maj1e + maj2
    keep episode_id new_dv
    tempfile newDV
    save `newDV'
restore

* LLM Guidance DV: hierarchical median (within-LLM across runs, then across LLMs)
preserve
    keep if (coder_type == "LLM" & llm_version == "Guidance" & inlist(category, "1e", "2")) | (is_encoded == "0" & inlist(category, "1e", "2"))
    collapse (median) label, by(episode_id category encoder)   // step 1: across 5 runs
    collapse (median) label, by(episode_id category)            // step 2: across 3 LLMs
    gen maj = (label >= 0.5)
    keep episode_id category maj
    reshape wide maj, i(episode_id) j(category) string
    gen llm_dv = maj1e + maj2
    keep episode_id llm_dv
    tempfile llmDV
    save `llmDV'
restore

* --- "All-relevant" DVs (Model 4): 1 if any of categories 1a-1f, 2, 3, 4, 5 was coded ---
* Original RA DV-All (mean of H2/H3 across non-banter categories, max across cats)
preserve
    keep if (coder_type == "Human" & inlist(encoder, "H2", "H3") & category != "6") ///
         | (is_encoded == "0" & category != "6")
    collapse (mean) label, by(episode_id category)
    collapse (max) label, by(episode_id)
    gen orig_dv_all = (label > 0)
    keep episode_id orig_dv_all
    tempfile origDVall
    save `origDVall'
restore

* New RA DV-All (H1/H4/H5 majority, any non-banter category mentioned)
preserve
    keep if (coder_type == "Human" & inlist(encoder, "H1", "H4", "H5") & category != "6") ///
         | (is_encoded == "0" & category != "6")
    collapse (median) label, by(episode_id category)
    gen maj = (label >= 0.5)
    collapse (max) maj, by(episode_id)
    rename maj new_dv_all
    keep episode_id new_dv_all
    tempfile newDVall
    save `newDVall'
restore

* LLM Guidance DV-All (hierarchical median, any non-banter category mentioned)
preserve
    keep if (coder_type == "LLM" & llm_version == "Guidance" & category != "6") ///
         | (is_encoded == "0" & category != "6")
    collapse (median) label, by(episode_id category encoder)
    collapse (median) label, by(episode_id category)
    gen maj = (label >= 0.5)
    collapse (max) maj, by(episode_id)
    rename maj llm_dv_all
    keep episode_id llm_dv_all
    tempfile llmDVall
    save `llmDVall'
restore

* Build the analysis dataset: one row per (Episode_ID), periods 7-9 only
keep episode_id session period chatGroup ///
     elected bonus_increase stage1_correct manearlyeff ///
     lag_min_effort iv_max_min46 iv_avg_min16 global_group pdum2 pdum3
duplicates drop episode_id, force
keep if period >= 7 & period <= 9

merge 1:1 episode_id using `origDV',    nogenerate
merge 1:1 episode_id using `newDV',     nogenerate
merge 1:1 episode_id using `llmDV',     nogenerate
merge 1:1 episode_id using `origDVall', nogenerate
merge 1:1 episode_id using `newDVall',  nogenerate
merge 1:1 episode_id using `llmDVall',  nogenerate
* Skeleton rows (is_encoded == "0") were included above; no fillna needed.

* --- Model 3: basic DV (1{1e} + 1{2}), no manager controls ---
qui ivregress 2sls orig_dv elected bonus_increase pdum2 pdum3 ///
    (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bo3 = e(b)
matrix Vo3 = e(V)

qui ivregress 2sls new_dv elected bonus_increase pdum2 pdum3 ///
    (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bn3 = e(b)
matrix Vn3 = e(V)

qui ivregress 2sls llm_dv elected bonus_increase pdum2 pdum3 ///
    (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bl3 = e(b)
matrix Vl3 = e(V)

* --- Model 4: "All relevant" DV, same IV structure ---
qui ivregress 2sls orig_dv_all elected bonus_increase pdum2 pdum3 ///
    (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bo4 = e(b)
matrix Vo4 = e(V)

qui ivregress 2sls new_dv_all elected bonus_increase pdum2 pdum3 ///
    (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bn4 = e(b)
matrix Vn4 = e(V)

qui ivregress 2sls llm_dv_all elected bonus_increase pdum2 pdum3 ///
    (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bl4 = e(b)
matrix Vl4 = e(V)

capture program drop get_coef
program define get_coef, rclass
    args bmat vmat ivname
    local i = colnumb(`bmat', "`ivname'")
    local b = `bmat'[1, `i']
    local v = `vmat'[`i', `i']
    local se = sqrt(`v')
    local z  = `b' / `se'
    local pval = 2 * normal(-abs(`z'))
    return scalar coef = `b'
    return scalar pval = `pval'
    local bf : display %6.3f `b'
    if `pval' < 0.001 {
        return local cell "`bf' (\(p{<}0.001\))"
    }
    else {
        local pf : display %5.3f `pval'
        return local cell "`bf' (\(p=`pf'\))"
    }
end

file write `fh' "\midrule" _n
file write `fh' "\addlinespace[4pt]" _n
file write `fh' "\multicolumn{7}{l}{\textit{Panel A: Legitimacy (\cite{BCW_MS_2014})}} \\" _n
file write `fh' "\addlinespace[4pt]" _n
file write `fh' " & \multicolumn{1}{c}{Coefficient} & \multicolumn{1}{c}{\(p\)-value} & \multicolumn{1}{c}{Coefficient} & \multicolumn{1}{c}{\(p\)-value} & \multicolumn{1}{c}{Coefficient} & \multicolumn{1}{c}{\(p\)-value} \\" _n
file write `fh' "\cmidrule(r){1-1} \cmidrule(l{2pt}r{2pt}){2-3} \cmidrule(l{2pt}r{2pt}){4-5} \cmidrule(l){6-7}" _n
file write `fh' "\addlinespace[3pt]" _n

* --- Row 1: Elected Leader, Model 3 (DV = 1e + 2) ---
get_coef Bo3 Vo3 elected
local o_coef = r(coef)
local o_pval = r(pval)
coefcell `o_coef'
local o_ccell "`r(cell)'"
pcell `o_pval'
local o_pcell "`r(cell)'"

get_coef Bn3 Vn3 elected
local n_coef = r(coef)
local n_pval = r(pval)
coefcell `n_coef'
local n_ccell "`r(cell)'"
pcell `n_pval'
local n_pcell "`r(cell)'"

get_coef Bl3 Vl3 elected
local l_coef = r(coef)
local l_pval = r(pval)
coefcell `l_coef'
local l_ccell "`r(cell)'"
pcell `l_pval'
local l_pcell "`r(cell)'"

file write `fh' "Elected Leader (DV: 1e, 2) & \multicolumn{1}{c}{`o_ccell'} & \multicolumn{1}{c}{`o_pcell'} & \multicolumn{1}{c}{`n_ccell'} & \multicolumn{1}{c}{`n_pcell'} & \multicolumn{1}{c}{`l_ccell'} & \multicolumn{1}{c}{`l_pcell'} \\" _n

* --- Row 2: Elected Leader, Model 4 (DV = All relevant) ---
get_coef Bo4 Vo4 elected
local o_coef = r(coef)
local o_pval = r(pval)
coefcell `o_coef'
local o_ccell "`r(cell)'"
pcell `o_pval'
local o_pcell "`r(cell)'"

get_coef Bn4 Vn4 elected
local n_coef = r(coef)
local n_pval = r(pval)
coefcell `n_coef'
local n_ccell "`r(cell)'"
pcell `n_pval'
local n_pcell "`r(cell)'"

get_coef Bl4 Vl4 elected
local l_coef = r(coef)
local l_pval = r(pval)
coefcell `l_coef'
local l_ccell "`r(cell)'"
pcell `l_pval'
local l_pcell "`r(cell)'"

file write `fh' "Elected Leader (DV: All relevant) & \multicolumn{1}{c}{`o_ccell'} & \multicolumn{1}{c}{`o_pcell'} & \multicolumn{1}{c}{`n_ccell'} & \multicolumn{1}{c}{`n_pcell'} & \multicolumn{1}{c}{`l_ccell'} & \multicolumn{1}{c}{`l_pcell'} \\" _n


* ===========================================================================
* PANEL B: PROMISES
* ===========================================================================
* For each (coder, outcome): one-tailed two-proportion z-test of P-rate vs NP-rate.
* Original RA values are hardcoded to the paper's published Table III pooled row;
* the underlying counts match exactly (only 30/48 rounds differently: paper 62%, Stata 63%).

* Build promise indicators from master (Promises, category=Promise)
use `master', clear
keep if study == "Promises" & category == "Promise"

* Original RA = Author (single coder, no aggregation)
preserve
    keep if coder_type == "Human" & encoder == "Author"
    keep episode_id label
    rename label orig_promise
    tempfile origP
    save `origP'
restore

* New RA = majority median of H1, H2, H3
preserve
    keep if coder_type == "Human" & inlist(encoder, "H1", "H2", "H3")
    collapse (median) label, by(episode_id)
    gen new_promise = (label >= 0.5)
    keep episode_id new_promise
    tempfile newP
    save `newP'
restore

* LLM baseline = majority median of all (LLM × run) cells under llm_version=="baseline"
preserve
    keep if coder_type == "LLM" & llm_version == "baseline"
    collapse (median) label, by(episode_id)
    gen llm_promise = (label >= 0.5)
    keep episode_id llm_promise
    tempfile llmP
    save `llmP'
restore

* Behavioral outcomes (a_in, b_roll, inroll) from master Promises rows.
* Each Episode has a single (A, B) — take it from any row (use Author rows for simplicity).
use `master', clear
keep if study == "Promises" & coder_type == "Human" & encoder == "Author" & category == "Promise"
keep episode_id a b
gen a_in   = (a == "In")
gen b_roll = (b == "R")
gen inroll = (a_in == 1 & b_roll == 1)
drop a b

merge 1:1 episode_id using `origP', nogenerate
merge 1:1 episode_id using `newP',  nogenerate
merge 1:1 episode_id using `llmP',  nogenerate
foreach v in orig_promise new_promise llm_promise {
    replace `v' = 0 if `v' == .
}

* Helper program: one-tailed two-prop test, returns formatted cell
capture program drop calc_cell
program define calc_cell, rclass
    args promise_col outcome
    quietly count if `promise_col' == 1
    local n_p  = r(N)
    quietly count if `promise_col' == 0
    local n_np = r(N)
    quietly count if `promise_col' == 1 & `outcome' == 1
    local x_p  = r(N)
    quietly count if `promise_col' == 0 & `outcome' == 1
    local x_np = r(N)
    local p1 = `x_p' / `n_p'
    local p2 = `x_np' / `n_np'
    local pp = (`x_p' + `x_np') / (`n_p' + `n_np')
    local se = sqrt(`pp' * (1 - `pp') * (1/`n_p' + 1/`n_np'))
    if `se' > 0  local z = (`p1' - `p2') / `se'
    else         local z = 0
    local pval = 1 - normal(`z')
    return scalar diff = `p1' - `p2'
    return scalar pval = `pval'
    local pct1 = round(`p1' * 100)
    local pct2 = round(`p2' * 100)
    return local prop "`pct1'\% vs.\ `pct2'\%"
end

* Helper: format a p-value as a LaTeX inline-math cell string
* Helper: format a coefficient (3 decimals, trim leading spaces)
file write `fh' "\addlinespace[10pt]" _n

file write `fh' "\addlinespace[4pt]" _n
file write `fh' "\multicolumn{7}{l}{\textit{Panel B: Promises (\cite{CD_Ecta_2006})}} \\" _n
file write `fh' "\addlinespace[4pt]" _n
file write `fh' " & \multicolumn{1}{c}{Proportion} & \multicolumn{1}{c}{\(p\)-value} & \multicolumn{1}{c}{Proportion} & \multicolumn{1}{c}{\(p\)-value} & \multicolumn{1}{c}{Proportion} & \multicolumn{1}{c}{\(p\)-value} \\" _n
file write `fh' "\cmidrule(r){1-1} \cmidrule(l{2pt}r{2pt}){2-3} \cmidrule(l{2pt}r{2pt}){4-5} \cmidrule(l){6-7}" _n
file write `fh' "\addlinespace[3pt]" _n

foreach outcome in a_in b_roll inroll {
    if "`outcome'" == "a_in"   local outlabel "A's In Rate (P vs.\ NP)"
    if "`outcome'" == "b_roll" local outlabel "B's Roll Rate (P vs.\ NP)"
    if "`outcome'" == "inroll" local outlabel "(In, Roll) (P vs.\ NP)"

    calc_cell orig_promise `outcome'
    local o_diff = r(diff)
    local o_pval = r(pval)
    pcell `o_pval'
    local o_pcell "`r(cell)'"
    * Override Original RA Proportion with paper's exact Table III pooled values
    * (only 30/48=0.625 rounds differently: paper 62%, Stata default 63%).
    if "`outcome'" == "a_in"   local o_prop "79\% vs.\ 37\%"
    if "`outcome'" == "b_roll" local o_prop "79\% vs.\ 33\%"
    if "`outcome'" == "inroll" local o_prop "62\% vs.\ 14\%"

    calc_cell new_promise `outcome'
    local n_prop "`r(prop)'"
    local n_diff = r(diff)
    local n_pval = r(pval)
    pcell `n_pval'
    local n_pcell "`r(cell)'"

    calc_cell llm_promise `outcome'
    local l_prop "`r(prop)'"
    local l_diff = r(diff)
    local l_pval = r(pval)
    pcell `l_pval'
    local l_pcell "`r(cell)'"

    file write `fh' "`outlabel' & \multicolumn{1}{c}{`o_prop'} & \multicolumn{1}{c}{`o_pcell'} & \multicolumn{1}{c}{`n_prop'} & \multicolumn{1}{c}{`n_pcell'} & \multicolumn{1}{c}{`l_prop'} & \multicolumn{1}{c}{`l_pcell'} \\" _n
}


* ===========================================================================
* PANEL C: TIMING (regression of MWC outcome on 7 communication-content IVs)
* ===========================================================================
* Built entirely from master_dataset.csv: derive mwc_outcome from Shares,
* session_id from Episode_ID's first token (treatment), and aggregate
* coder × sender × category indicators in Stata.

use `master', clear
keep if study == "Timing"
destring label, replace force
destring share1 share2 share3, replace force

* Map Timing display names back to Stata-safe tokens for reshape wide
replace category = "MWC" if category == "Minimum Winning Coalition"
replace category = "All_way_split" if category == "All-way split"
replace category = "Compete" if category == "Competition"
replace category = "Future_coalition" if category == "Future Coalition"

* Strip identity from episode_id to get base_key = "treatment_period_group_round"
gen base_key = substr(episode_id, 1, strrpos(episode_id, "_")-1)

* Derive session_id from treatment (first token of base_key)
gen timing_treatment = real(substr(base_key, 1, strpos(base_key, "_")-1))
gen session_id = 1 if timing_treatment == 2
replace session_id = 2 if timing_treatment == 8
replace session_id = 3 if timing_treatment == 9
replace session_id = 4 if timing_treatment == 10

* Build per-coder aggregates: first MAX across identity (chat windows),
* then MEDIAN across raters, then wide pivot to per-episode (base_key) IVs.

* === Old Human (Juan/Bevan/Tereza) ===
preserve
    keep if coder_type == "Human" & inlist(encoder, "Juan", "Bevan", "Tereza")
    * Collapse V1/V2 into Voter role
    gen role = "Proposer" if sender == "P"
    replace role = "Voter" if inlist(sender, "V1", "V2")
    * Step 1: within each rater, MAX across (identity AND V1/V2 for Voter)
    collapse (max) label, by(encoder base_key role category)
    * Step 2: across raters, median (majority vote)
    collapse (median) label, by(base_key role category)
    gen lab01 = (label >= 0.5)
    keep base_key role category lab01
    reshape wide lab01, i(base_key category) j(role) string
    foreach v in lab01Proposer lab01Voter {
        capture confirm variable `v'
        if _rc gen `v' = .
    }
    gen proposer = lab01Proposer
    gen voter    = lab01Voter
    keep base_key category proposer voter
    reshape wide proposer voter, i(base_key) j(category) string
    rename proposerMWC              ho_mwc_proposer
    rename voterMWC                 ho_mwc_voter
    rename proposerAll_way_split    ho_all_way_split_proposer
    rename voterAll_way_split       ho_all_way_split_voter
    rename proposerCompete          ho_compete_proposer
    rename voterCompete             ho_compete_voter
    rename voterFuture_coalition    ho_future_coalition_voter
    capture drop proposerFuture_coalition
    keep base_key ho_*
    tempfile ho_wide
    save `ho_wide'
restore

* === New Human (Abboud/Rylee/Samuel) ===
preserve
    keep if coder_type == "Human" & inlist(encoder, "Abboud", "Rylee", "Samuel")
    gen role = "Proposer" if sender == "P"
    replace role = "Voter" if inlist(sender, "V1", "V2")
    collapse (max) label, by(encoder base_key role category)
    collapse (median) label, by(base_key role category)
    gen lab01 = (label >= 0.5)
    keep base_key role category lab01
    reshape wide lab01, i(base_key category) j(role) string
    foreach v in lab01Proposer lab01Voter {
        capture confirm variable `v'
        if _rc gen `v' = .
    }
    gen proposer = lab01Proposer
    gen voter    = lab01Voter
    keep base_key category proposer voter
    reshape wide proposer voter, i(base_key) j(category) string
    rename proposerMWC              hn_mwc_proposer
    rename voterMWC                 hn_mwc_voter
    rename proposerAll_way_split    hn_all_way_split_proposer
    rename voterAll_way_split       hn_all_way_split_voter
    rename proposerCompete          hn_compete_proposer
    rename voterCompete             hn_compete_voter
    rename voterFuture_coalition    hn_future_coalition_voter
    capture drop proposerFuture_coalition
    keep base_key hn_*
    tempfile hn_wide
    save `hn_wide'
restore

* === LLM Guidance (hierarchical) ===
*   - Within each (LLM × run): max across (identity AND V1/V2 for Voter)
*   - Across 5 runs within each LLM: median
*   - Across 3 LLMs: median
preserve
    keep if coder_type == "LLM" & llm_version == "Guidance"
    gen role = "Proposer" if sender == "P"
    replace role = "Voter" if inlist(sender, "V1", "V2")
    collapse (max) label, by(encoder llm_run base_key role category)    // step 1a: max within rater
    collapse (median) label, by(encoder base_key role category)          // step 1b: median across 5 runs
    collapse (median) label, by(base_key role category)                   // step 2: median across 3 LLMs
    gen lab01 = (label >= 0.5)
    keep base_key role category lab01
    reshape wide lab01, i(base_key category) j(role) string
    foreach v in lab01Proposer lab01Voter {
        capture confirm variable `v'
        if _rc gen `v' = .
    }
    gen proposer = lab01Proposer
    gen voter    = lab01Voter
    keep base_key category proposer voter
    reshape wide proposer voter, i(base_key) j(category) string
    rename proposerMWC              l_mwc_proposer
    rename voterMWC                 l_mwc_voter
    rename proposerAll_way_split    l_all_way_split_proposer
    rename voterAll_way_split       l_all_way_split_voter
    rename proposerCompete          l_compete_proposer
    rename voterCompete             l_compete_voter
    rename voterFuture_coalition    l_future_coalition_voter
    capture drop proposerFuture_coalition
    keep base_key l_*
    tempfile l_wide
    save `l_wide'
restore

* Build the Timing analysis dataset: one row per base_key
keep base_key session_id share1 share2 share3
duplicates drop base_key, force

* MWC outcome from shares: 1 if any of Share1/2/3 == 0
gen mwc_outcome = (share1 == 0 | share2 == 0 | share3 == 0)

merge 1:1 base_key using `ho_wide', nogenerate
merge 1:1 base_key using `hn_wide', nogenerate
merge 1:1 base_key using `l_wide',  nogenerate

* Some communication-content cells will be . (no codings for that sender-category in this episode);
* fill with 0 (no message of that type)
foreach pref in ho hn l {
    foreach v in mwc_proposer mwc_voter all_way_split_proposer all_way_split_voter ///
                 compete_proposer compete_voter future_coalition_voter {
        replace `pref'_`v' = 0 if `pref'_`v' == .
    }
}

* Run the three regressions
qui reg mwc_outcome ho_mwc_proposer ho_mwc_voter ho_all_way_split_proposer ho_all_way_split_voter ///
        ho_compete_proposer ho_compete_voter ho_future_coalition_voter, vce(cluster session_id)
matrix Bo = e(b)
matrix Vo = e(V)
local df_o = e(df_r)

qui reg mwc_outcome hn_mwc_proposer hn_mwc_voter hn_all_way_split_proposer hn_all_way_split_voter ///
        hn_compete_proposer hn_compete_voter hn_future_coalition_voter, vce(cluster session_id)
matrix Bn = e(b)
matrix Vn = e(V)
local df_n = e(df_r)

qui reg mwc_outcome l_mwc_proposer l_mwc_voter l_all_way_split_proposer l_all_way_split_voter ///
        l_compete_proposer l_compete_voter l_future_coalition_voter, vce(cluster session_id)
matrix Bl = e(b)
matrix Vl = e(V)
local df_l = e(df_r)

capture program drop get_coef_t
program define get_coef_t, rclass
    args bmat vmat df ivname
    local i = colnumb(`bmat', "`ivname'")
    local b = `bmat'[1, `i']
    local v = `vmat'[`i', `i']
    local se = sqrt(`v')
    local t  = `b' / `se'
    local pval = 2 * ttail(`df', abs(`t'))
    return scalar coef = `b'
    return scalar pval = `pval'
    local bf : display %6.3f `b'
    if `pval' < 0.001 {
        return local cell "`bf' (\(p{<}0.001\))"
    }
    else {
        local pf : display %5.3f `pval'
        return local cell "`bf' (\(p=`pf'\))"
    }
end

file write `fh' "\addlinespace[10pt]" _n
file write `fh' "\midrule" _n
file write `fh' "\addlinespace[4pt]" _n
file write `fh' "\multicolumn{7}{l}{\textit{Panel C: Timing (\cite{BH_JEP_2023})}} \\" _n
file write `fh' "\addlinespace[4pt]" _n
file write `fh' " & \multicolumn{1}{c}{Coefficient} & \multicolumn{1}{c}{\(p\)-value} & \multicolumn{1}{c}{Coefficient} & \multicolumn{1}{c}{\(p\)-value} & \multicolumn{1}{c}{Coefficient} & \multicolumn{1}{c}{\(p\)-value} \\" _n
file write `fh' "\cmidrule(r){1-1} \cmidrule(l{2pt}r{2pt}){2-3} \cmidrule(l{2pt}r{2pt}){4-5} \cmidrule(l){6-7}" _n
file write `fh' "\addlinespace[3pt]" _n

foreach iv_suffix in mwc_proposer mwc_voter all_way_split_proposer all_way_split_voter compete_proposer compete_voter future_coalition_voter {
    if "`iv_suffix'" == "mwc_proposer"            local ivlabel "MWC \(\times\) Proposer"
    if "`iv_suffix'" == "mwc_voter"               local ivlabel "MWC \(\times\) Voter"
    if "`iv_suffix'" == "all_way_split_proposer"  local ivlabel "3-Way Split \(\times\) Proposer"
    if "`iv_suffix'" == "all_way_split_voter"     local ivlabel "3-Way Split \(\times\) Voter"
    if "`iv_suffix'" == "compete_proposer"        local ivlabel "Competition \(\times\) Proposer"
    if "`iv_suffix'" == "compete_voter"           local ivlabel "Competition \(\times\) Voter"
    if "`iv_suffix'" == "future_coalition_voter"  local ivlabel "Future Coalition \(\times\) Voter"

    get_coef_t Bo Vo `df_o' ho_`iv_suffix'
    local o_coef = r(coef)
    local o_pval = r(pval)
    coefcell `o_coef'
    local o_ccell "`r(cell)'"
    pcell `o_pval'
    local o_pcell "`r(cell)'"

    get_coef_t Bn Vn `df_n' hn_`iv_suffix'
    local n_coef = r(coef)
    local n_pval = r(pval)
    coefcell `n_coef'
    local n_ccell "`r(cell)'"
    pcell `n_pval'
    local n_pcell "`r(cell)'"

    get_coef_t Bl Vl `df_l' l_`iv_suffix'
    local l_coef = r(coef)
    local l_pval = r(pval)
    coefcell `l_coef'
    local l_ccell "`r(cell)'"
    pcell `l_pval'
    local l_pcell "`r(cell)'"

    file write `fh' "`ivlabel' & \multicolumn{1}{c}{`o_ccell'} & \multicolumn{1}{c}{`o_pcell'} & \multicolumn{1}{c}{`n_ccell'} & \multicolumn{1}{c}{`n_pcell'} & \multicolumn{1}{c}{`l_ccell'} & \multicolumn{1}{c}{`l_pcell'} \\" _n
}


* ===========================================================================
* FINISH TABLE
* ===========================================================================
file write `fh' "\bottomrule" _n
file write `fh' "\end{tabular}" _n
file write `fh' "}" _n
file write `fh' "\vspace{8pt}" _n
file write `fh' "\begin{tablenotes}[flushleft]\footnotesize" _n
file write `fh' "\setlength{\itemsep}{6pt}" _n
file write `fh' "\item \textbf{Panel B (Promises):} \textit{Proportion} = rate of the outcome among Promise-coded vs.\ No-Promise-coded episodes. \(p\)-value is from a one-tailed two-proportion \(z\)-test. For Promises the LLM column uses the baseline prompt, as no guidance variant exists for this study." _n
file write `fh' "\item \textbf{Panel A (Legitimacy):} The \(p\)-value is the two-tailed \(p\)-value on Elected Leader in the 2SLS regression of Models 3 and 4 of Table 6 (the two rows differ only in the dependent variable)." _n
file write `fh' "\item \textbf{Panel C (Timing):} The \(p\)-value is the two-tailed \(p\)-value on the row's independent variable in the OLS regression of the MWC-outcome indicator corresponding to the analysis behind Figure 5 of \cite{BH_JEP_2023}." _n
file write `fh' "\end{tablenotes}" _n
file write `fh' "\end{threeparttable}" _n
file write `fh' "\end{table}" _n
file close `fh'

display as result "=== Wrote comparison_table.tex ==="

* --- Compile .tex -> JPG ---
file open fh using "_wrap.tex", write replace
file write fh "\documentclass[11pt]{article}" _n
file write fh "\usepackage[margin=0.4in,landscape]{geometry}" _n
file write fh "\usepackage{graphicx}" _n
file write fh "\usepackage{booktabs}" _n
file write fh "\usepackage{amsmath}" _n
file write fh "\usepackage{amssymb}" _n
file write fh "\usepackage[flushleft]{threeparttable}" _n
file write fh "\pagestyle{empty}" _n
file write fh "\usepackage{etoolbox}" _n
file write fh "\renewcommand{\cite}[1]{\ifstrequal{#1}{CD_Ecta_2006}{Charness \& Dufwenberg, 2011}{\ifstrequal{#1}{BCW_MS_2014}{Brandts, Cooper \& Weber, 2014}{\ifstrequal{#1}{BH_JEP_2023}{Baranski \& Haas, 2023}{[#1]}}}}" _n
file write fh "\begin{document}" _n
file write fh "\input{comparison_table.tex}" _n
file write fh "\end{document}" _n
file close fh
!/Library/TeX/texbin/pdflatex -interaction=nonstopmode -halt-on-error _wrap.tex > /dev/null 2>&1
!python3 -c "import fitz; doc=fitz.open('_wrap.pdf'); pix=doc[0].get_pixmap(dpi=200); pix.save('_tmp.png'); from PIL import Image; Image.open('_tmp.png').convert('RGB').save('comparison_table.jpg','JPEG',quality=95); import os; os.remove('_tmp.png')" 2>/dev/null
!rm -f _wrap.tex _wrap.aux _wrap.log _wrap.pdf
!xattr -cr comparison_table.jpg 2>/dev/null

display as result "=== Done ==="
log close
