*! Cross-study comparison table — SIMPLIFIED version (master format)
*! Columns: Outcome | p-value (Original, RA-based, LLM-based)
*!                  | Match Sign (Original-RA, RA-LLM)
*!                  | Match Significance (Original-RA, RA-LLM)
*! Panel A = Legitimacy Models 3 & 4 (Elected Leader: Use 40 / Relevant)
*! Panel B = Promises (3 behavioral outcomes); Panel C = Timing (7 IVs).
*! LLM column = llm_version "Base" (this is the LLM Baseline table).
*! Significance for "Match Significance" uses the p < 0.10 threshold.
*! Reads ONLY ../../../master_dataset.csv. Output written with \(...\); a final
*! sed pass converts \( \) -> $ to match the paper's dollar-math style.

clear all
set more off
capture log close
log using "comparison_table.log", replace text

local SIGCUT 0.10

import delimited "../../../data/master_dataset.csv", clear stringcols(_all)
destring label, replace force
tempfile master
save `master'

* ===========================================================================
* HELPER PROGRAMS
* ===========================================================================
capture program drop pcellD
program define pcellD, rclass
    args pval
    if `pval' < 0.001 {
        return local cell "\(p{<}0.001\)"
    }
    else {
        local pf : display %5.3f `pval'
        return local cell "\(p=`pf'\)"
    }
end

capture program drop ynsign
program define ynsign, rclass
    args a b
    if (`a' > 0 & `b' > 0) | (`a' < 0 & `b' < 0) return local yn "Yes"
    else                                          return local yn "No"
end

capture program drop ynsig
program define ynsig, rclass
    args p1 p2 cut
    local s1 = (`p1' < `cut')
    local s2 = (`p2' < `cut')
    if `s1' == `s2' return local yn "Yes"
    else            return local yn "No"
end

capture program drop get_coef
program define get_coef, rclass
    args bmat vmat ivname
    local i = colnumb(`bmat', "`ivname'")
    local b = `bmat'[1, `i']
    local se = sqrt(`vmat'[`i', `i'])
    local pval = 2 * normal(-abs(`b'/`se'))
    return scalar coef = `b'
    return scalar pval = `pval'
end

capture program drop get_coef_t
program define get_coef_t, rclass
    args bmat vmat df ivname
    local i = colnumb(`bmat', "`ivname'")
    local b = `bmat'[1, `i']
    local se = sqrt(`vmat'[`i', `i'])
    local pval = 2 * ttail(`df', abs(`b'/`se'))
    return scalar coef = `b'
    return scalar pval = `pval'
end

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
    return scalar diff = `p1' - `p2'
    return scalar pval = 1 - normal(`z')
end

capture program drop writerow
program define writerow
    args fh label o_p n_p l_p o_c n_c l_c cut
    pcellD `o_p'
    local op "`r(cell)'"
    pcellD `n_p'
    local np "`r(cell)'"
    pcellD `l_p'
    local lp "`r(cell)'"
    ynsign `o_c' `n_c'
    local sgnOR "`r(yn)'"
    ynsign `n_c' `l_c'
    local sgnRL "`r(yn)'"
    ynsig `o_p' `n_p' `cut'
    local sigOR "`r(yn)'"
    ynsig `n_p' `l_p' `cut'
    local sigRL "`r(yn)'"
    file write `fh' "`label' & `op' & `np' & `lp' & `sgnOR' & `sgnRL' & `sigOR' & `sigRL' \\" _n
end

* ===========================================================================
* OPEN OUTPUT + PREAMBLE (paper's landscape format)
* ===========================================================================
tempname fh
file open `fh' using "comparison_table.tex", write replace
file write `fh' "\begin{landscape}" _n
file write `fh' "\thispagestyle{empty}" _n
file write `fh' "\centering" _n
file write `fh' "\vspace*{\fill}" _n
file write `fh' "\renewcommand{\arraystretch}{0.75}" _n
file write `fh' "\small" _n
file write `fh' "\begin{threeparttable}" _n
file write `fh' "\captionof{table}{Experimental Behavior and Communication Content: Replicating Statistical Analyses with Different Codings}" _n
file write `fh' "\label{tab:cross-study-replication}" _n
file write `fh' "\begin{tabular}{l@{\hskip 20pt} ccc @{\hskip 20pt} cc @{\hskip 20pt} cc}" _n
file write `fh' "\toprule" _n
file write `fh' "\textbf{Outcome} & \multicolumn{3}{c}{\textbf{\(p\)-value}} & \multicolumn{2}{c}{\textbf{Match Sign}} & \multicolumn{2}{c}{\textbf{Match Significance}} \\" _n
file write `fh' "\cmidrule(lr){2-4} \cmidrule(lr){5-6} \cmidrule(lr){7-8}" _n
file write `fh' " & Original & RA-based & LLM-based & Original--RA & RA--LLM & Original--RA & RA--LLM \\" _n
file write `fh' "\midrule" _n

* ===========================================================================
* PANEL A: LEGITIMACY (Models 3 and 4)
* ===========================================================================
use `master', clear
keep if study == "Legitimacy"
destring label, replace force
split episode_id, parse("_") destring gen(eid_)
rename eid_1 session
rename eid_2 period
rename eid_3 chatGroup
destring bonus_increase global_group lag_min_effort iv_max_min46 iv_avg_min16 ///
         elected stage1_correct manearlyeff, replace force
gen pdum2 = (period == 8)
gen pdum3 = (period == 9)

preserve
    keep if (coder_type == "Human" & inlist(encoder, "H2", "H3") & inlist(category, "1e", "2")) | (is_encoded == "0" & inlist(category, "1e", "2"))
    collapse (mean) label, by(episode_id category)
    reshape wide label, i(episode_id) j(category) string
    gen orig_dv = label1e + label2
    keep episode_id orig_dv
    tempfile origDV
    save `origDV'
restore
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
preserve
    keep if (coder_type == "LLM" & llm_version == "Base" & inlist(category, "1e", "2")) | (is_encoded == "0" & inlist(category, "1e", "2"))
    collapse (median) label, by(episode_id category encoder)
    collapse (median) label, by(episode_id category)
    gen maj = (label >= 0.5)
    keep episode_id category maj
    reshape wide maj, i(episode_id) j(category) string
    gen llm_dv = maj1e + maj2
    keep episode_id llm_dv
    tempfile llmDV
    save `llmDV'
restore
preserve
    keep if (coder_type == "Human" & inlist(encoder, "H2", "H3") & category != "6") | (is_encoded == "0" & category != "6")
    collapse (mean) label, by(episode_id category)
    collapse (max) label, by(episode_id)
    gen orig_dv_all = (label > 0)
    keep episode_id orig_dv_all
    tempfile origDVall
    save `origDVall'
restore
preserve
    keep if (coder_type == "Human" & inlist(encoder, "H1", "H4", "H5") & category != "6") | (is_encoded == "0" & category != "6")
    collapse (median) label, by(episode_id category)
    gen maj = (label >= 0.5)
    collapse (max) maj, by(episode_id)
    rename maj new_dv_all
    keep episode_id new_dv_all
    tempfile newDVall
    save `newDVall'
restore
preserve
    keep if (coder_type == "LLM" & llm_version == "Base" & category != "6") | (is_encoded == "0" & category != "6")
    collapse (median) label, by(episode_id category encoder)
    collapse (median) label, by(episode_id category)
    gen maj = (label >= 0.5)
    collapse (max) maj, by(episode_id)
    rename maj llm_dv_all
    keep episode_id llm_dv_all
    tempfile llmDVall
    save `llmDVall'
restore

keep episode_id session period chatGroup elected bonus_increase stage1_correct manearlyeff ///
     lag_min_effort iv_max_min46 iv_avg_min16 global_group pdum2 pdum3
duplicates drop episode_id, force
keep if period >= 7 & period <= 9
merge 1:1 episode_id using `origDV',    nogenerate
merge 1:1 episode_id using `newDV',     nogenerate
merge 1:1 episode_id using `llmDV',     nogenerate
merge 1:1 episode_id using `origDVall', nogenerate
merge 1:1 episode_id using `newDVall',  nogenerate
merge 1:1 episode_id using `llmDVall',  nogenerate

qui ivregress 2sls orig_dv elected bonus_increase pdum2 pdum3 (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bo3 = e(b)
matrix Vo3 = e(V)
qui ivregress 2sls new_dv  elected bonus_increase pdum2 pdum3 (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bn3 = e(b)
matrix Vn3 = e(V)
qui ivregress 2sls llm_dv  elected bonus_increase pdum2 pdum3 (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bl3 = e(b)
matrix Vl3 = e(V)
qui ivregress 2sls orig_dv_all elected bonus_increase pdum2 pdum3 (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bo4 = e(b)
matrix Vo4 = e(V)
qui ivregress 2sls new_dv_all  elected bonus_increase pdum2 pdum3 (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bn4 = e(b)
matrix Vn4 = e(V)
qui ivregress 2sls llm_dv_all  elected bonus_increase pdum2 pdum3 (lag_min_effort = iv_max_min46 iv_avg_min16), vce(cluster global_group)
matrix Bl4 = e(b)
matrix Vl4 = e(V)

file write `fh' "\addlinespace[4pt]" _n
file write `fh' "\multicolumn{8}{l}{\textit{Panel A: Legitimacy (\cite{BCW_MS_2014})}} \\" _n
file write `fh' "\addlinespace[2pt]" _n
file write `fh' "\cmidrule(lr){1-1} \cmidrule(lr){2-4} \cmidrule(lr){5-6} \cmidrule(lr){7-8}" _n
file write `fh' "\addlinespace[3pt]" _n

get_coef Bo3 Vo3 elected
local o_p = r(pval)
local o_c = r(coef)
get_coef Bn3 Vn3 elected
local n_p = r(pval)
local n_c = r(coef)
get_coef Bl3 Vl3 elected
local l_p = r(pval)
local l_c = r(coef)
writerow `fh' "Elected Leader (DV: Use 40)" `o_p' `n_p' `l_p' `o_c' `n_c' `l_c' `SIGCUT'

get_coef Bo4 Vo4 elected
local o_p = r(pval)
local o_c = r(coef)
get_coef Bn4 Vn4 elected
local n_p = r(pval)
local n_c = r(coef)
get_coef Bl4 Vl4 elected
local l_p = r(pval)
local l_c = r(coef)
writerow `fh' "Elected Leader (DV: Relevant)" `o_p' `n_p' `l_p' `o_c' `n_c' `l_c' `SIGCUT'

* ===========================================================================
* PANEL B: PROMISES
* ===========================================================================
use `master', clear
keep if study == "Promises" & category == "Promise"
preserve
    keep if coder_type == "Human" & encoder == "Author"
    keep episode_id label
    rename label orig_promise
    tempfile origP
    save `origP'
restore
preserve
    keep if coder_type == "Human" & inlist(encoder, "H1", "H2", "H3")
    collapse (median) label, by(episode_id)
    gen new_promise = (label >= 0.5)
    keep episode_id new_promise
    tempfile newP
    save `newP'
restore
preserve
    keep if coder_type == "LLM" & llm_version == "Base"
    collapse (median) label, by(episode_id)
    gen llm_promise = (label >= 0.5)
    keep episode_id llm_promise
    tempfile llmP
    save `llmP'
restore
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

file write `fh' "\addlinespace[10pt]" _n
file write `fh' "\multicolumn{8}{l}{\textit{Panel B: Promises (\cite{CD_Ecta_2006})}} \\" _n
file write `fh' "\addlinespace[2pt]" _n
file write `fh' "\cmidrule(lr){1-1} \cmidrule(lr){2-4} \cmidrule(lr){5-6} \cmidrule(lr){7-8}" _n
file write `fh' "\addlinespace[3pt]" _n

foreach outcome in a_in b_roll inroll {
    if "`outcome'" == "a_in"   local outlabel "A's In Rate (P vs.\ NP)"
    if "`outcome'" == "b_roll" local outlabel "B's Roll Rate (P vs.\ NP)"
    if "`outcome'" == "inroll" local outlabel "(In, Roll) (P vs.\ NP)"
    calc_cell orig_promise `outcome'
    local o_p = r(pval)
    local o_c = r(diff)
    calc_cell new_promise `outcome'
    local n_p = r(pval)
    local n_c = r(diff)
    calc_cell llm_promise `outcome'
    local l_p = r(pval)
    local l_c = r(diff)
    writerow `fh' "`outlabel'" `o_p' `n_p' `l_p' `o_c' `n_c' `l_c' `SIGCUT'
}

* ===========================================================================
* PANEL C: TIMING
* ===========================================================================
use `master', clear
keep if study == "Timing"
destring label share1 share2 share3, replace force
replace category = "MWC" if category == "Minimum Winning Coalition"
replace category = "All_way_split" if category == "All-way split"
replace category = "Compete" if category == "Competition"
replace category = "Future_coalition" if category == "Future Coalition"
gen base_key = substr(episode_id, 1, strrpos(episode_id, "_")-1)
gen timing_treatment = real(substr(base_key, 1, strpos(base_key, "_")-1))
gen session_id = 1 if timing_treatment == 2
replace session_id = 2 if timing_treatment == 8
replace session_id = 3 if timing_treatment == 9
replace session_id = 4 if timing_treatment == 10

preserve
    keep if coder_type == "Human" & inlist(encoder, "Juan", "Bevan", "Tereza")
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
preserve
    keep if coder_type == "LLM" & llm_version == "Base"
    gen role = "Proposer" if sender == "P"
    replace role = "Voter" if inlist(sender, "V1", "V2")
    collapse (max) label, by(encoder llm_run base_key role category)
    collapse (median) label, by(encoder base_key role category)
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

keep base_key session_id share1 share2 share3
duplicates drop base_key, force
gen mwc_outcome = (share1 == 0 | share2 == 0 | share3 == 0)
merge 1:1 base_key using `ho_wide', nogenerate
merge 1:1 base_key using `hn_wide', nogenerate
merge 1:1 base_key using `l_wide',  nogenerate
foreach pref in ho hn l {
    foreach v in mwc_proposer mwc_voter all_way_split_proposer all_way_split_voter ///
                 compete_proposer compete_voter future_coalition_voter {
        replace `pref'_`v' = 0 if `pref'_`v' == .
    }
}

qui reg mwc_outcome ho_mwc_proposer ho_mwc_voter ho_all_way_split_proposer ho_all_way_split_voter ho_compete_proposer ho_compete_voter ho_future_coalition_voter, vce(cluster session_id)
matrix Bo = e(b)
matrix Vo = e(V)
local df_o = e(df_r)
qui reg mwc_outcome hn_mwc_proposer hn_mwc_voter hn_all_way_split_proposer hn_all_way_split_voter hn_compete_proposer hn_compete_voter hn_future_coalition_voter, vce(cluster session_id)
matrix Bn = e(b)
matrix Vn = e(V)
local df_n = e(df_r)
qui reg mwc_outcome l_mwc_proposer l_mwc_voter l_all_way_split_proposer l_all_way_split_voter l_compete_proposer l_compete_voter l_future_coalition_voter, vce(cluster session_id)
matrix Bl = e(b)
matrix Vl = e(V)
local df_l = e(df_r)

file write `fh' "\addlinespace[10pt]" _n
file write `fh' "\multicolumn{8}{l}{\textit{Panel C: Timing (\cite{BH_JEP_2023})}} \\" _n
file write `fh' "\addlinespace[2pt]" _n
file write `fh' "\cmidrule(lr){1-1} \cmidrule(lr){2-4} \cmidrule(lr){5-6} \cmidrule(lr){7-8}" _n
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
    local o_p = r(pval)
    local o_c = r(coef)
    get_coef_t Bn Vn `df_n' hn_`iv_suffix'
    local n_p = r(pval)
    local n_c = r(coef)
    get_coef_t Bl Vl `df_l' l_`iv_suffix'
    local l_p = r(pval)
    local l_c = r(coef)
    writerow `fh' "`ivlabel'" `o_p' `n_p' `l_p' `o_c' `n_c' `l_c' `SIGCUT'
}

* ===========================================================================
* FINISH
* ===========================================================================
file write `fh' "\bottomrule" _n
file write `fh' "\end{tabular}" _n
file write `fh' "\begin{tablenotes}[flushleft]" _n
file write `fh' "\footnotesize" _n
file write `fh' "\item \textbf{Panel A (Legitimacy):} The \(p\)-value is the two-tailed \(p\)-value for Elected Leader in the 2SLS regressions of Models 3 and 4 of Table 6." _n
file write `fh' "\item \textbf{Panel B (Promises):} The \(p\)-value comes from a one-tailed two-proportion \(z\)-test comparing the rate of each behavioral outcome between Promise-coded and No-Promise-coded episodes. The tests correspond to the third row (\textquotedblleft Pooled\textquotedblright) of Table III." _n
file write `fh' "\item \textbf{Panel C (Timing):} The \(p\)-value is the two-tailed \(p\)-value on the row's independent variable in the OLS regression of the MWC-outcome indicator corresponding to the analysis behind Figure 5." _n
file write `fh' "\end{tablenotes}" _n
file write `fh' "\end{threeparttable}" _n
file write `fh' "\end{landscape}" _n
file close `fh'

* convert \( \) -> $ to match the paper's dollar-math style
!sed -i '' 's/\\(/$/g; s/\\)/$/g' comparison_table.tex

display as result "=== Wrote comparison_table.tex ==="

* --- Compile preview JPG (landscape page, auto-cropped) ---
file open fh using "_wrap.tex", write replace
file write fh "\documentclass[11pt]{article}" _n
file write fh "\usepackage[landscape,margin=0.4in]{geometry}" _n
file write fh "\usepackage{graphicx}" _n
file write fh "\usepackage{booktabs}" _n
file write fh "\usepackage{amsmath}" _n
file write fh "\usepackage{amssymb}" _n
file write fh "\usepackage{array}" _n
file write fh "\usepackage[flushleft]{threeparttable}" _n
file write fh "\usepackage{capt-of}" _n
file write fh "\usepackage{pdflscape}" _n
file write fh "\renewenvironment{landscape}{}{}" _n
file write fh "\usepackage{etoolbox}" _n
file write fh "\renewcommand{\cite}[1]{\ifstrequal{#1}{CD_Ecta_2006}{Charness \& Dufwenberg, 2011}{\ifstrequal{#1}{BCW_MS_2014}{Brandts, Cooper \& Weber, 2014}{\ifstrequal{#1}{BH_JEP_2023}{Baranski \& Haas, 2023}{[#1]}}}}" _n
file write fh "\pagestyle{empty}" _n
file write fh "\begin{document}" _n
file write fh "\input{comparison_table.tex}" _n
file write fh "\end{document}" _n
file close fh
!/Library/TeX/texbin/pdflatex -interaction=nonstopmode -halt-on-error _wrap.tex > /dev/null 2>&1
!python3 -c "import fitz; from PIL import Image, ImageChops; doc=fitz.open('_wrap.pdf'); pix=doc[0].get_pixmap(dpi=200); pix.save('_tmp.png'); im=Image.open('_tmp.png').convert('RGB'); bg=Image.new('RGB',im.size,(255,255,255)); bb=ImageChops.difference(im,bg).getbbox(); im=(im.crop((max(bb[0]-25,0),max(bb[1]-25,0),min(bb[2]+25,im.size[0]),min(bb[3]+25,im.size[1])))) if bb else im; im.save('comparison_table.jpg','JPEG',quality=95)" 2>/dev/null
!rm -f _wrap.tex _wrap.aux _wrap.log _wrap.pdf _tmp.png
!xattr -cr comparison_table.jpg 2>/dev/null

display as result "=== Done ==="
log close
