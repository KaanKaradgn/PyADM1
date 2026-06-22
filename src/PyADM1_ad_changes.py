import numpy as np
import scipy.integrate
import pandas as pd

def get_ctm_multiplier(T, T_min=15.0, T_opt=37.0, T_max=44.0, T_ref=35.0):
    """
    Calculates Cardinal Temperature Model multiplier normalized to 35C.
    Ensures that when T=35, the multiplier is exactly 1.0.
    """
    if T <= T_min or T >= T_max:
        return 0.0
    
    def ctm_core(t_val):
        numerator = (t_val - T_max) * ((t_val - T_min) ** 2)
        denominator = (T_opt - T_min) * (
            (T_opt - T_min) * (t_val - T_opt) - 
            (T_opt - T_max) * (T_opt + T_min - 2 * t_val)
        )
        return numerator / denominator
    
    return ctm_core(T) / ctm_core(T_ref)

def run_adm1_simulation(influent_df, initial_df, load_factor=1.0, V_liq=3400.0):
    # --- 1. GLOBAL PHYSICAL CONSTANTS ---
    R = 0.083145 
    T_base = 298.15 
    p_atm = 1.013
    V_gas = 300.0
    k_La = 200.0
    k_p = 50000.0
    q_ad_standard = 178.46

    # --- 2. STOICHIOMETRIC PARAMETERS (Explicit Rows) ---
    f_sI_xc = 0.1
    f_xI_xc = 0.2
    f_ch_xc = 0.2
    f_pr_xc = 0.2
    f_li_xc = 0.3
    
    N_xc = 0.0026857  # 0.0376 / 14
    N_I = 0.0042857   # 0.06 / 14
    N_aa = 0.007
    N_bac = 0.0057143 # 0.08 / 14
    
    C_xc = 0.02786
    C_sI = 0.03
    C_ch = 0.0313
    C_pr = 0.03
    C_li = 0.022
    C_xI = 0.03
    C_su = 0.0313
    C_aa = 0.03
    C_fa = 0.0217
    C_bu = 0.025
    C_pro = 0.0268
    C_ac = 0.0313
    C_bac = 0.0313
    C_ch4 = 0.0156
    C_va = 0.024

    f_fa_li = 0.95
    f_h2_su = 0.19
    f_bu_su = 0.13
    f_pro_su = 0.27
    f_ac_su = 0.41
    
    f_h2_aa = 0.06
    f_va_aa = 0.23
    f_bu_aa = 0.26
    f_pro_aa = 0.05
    f_ac_aa = 0.40

    Y_su = 0.1
    Y_aa = 0.08
    Y_fa = 0.06
    Y_c4 = 0.06
    Y_pro = 0.04
    Y_ac = 0.05
    Y_h2 = 0.06

    # --- 3. BASE KINETIC PARAMETERS (Reference at 35C) ---
    k_dis_base = 0.5
    k_hyd_ch_base = 10.0
    k_hyd_pr_base = 10.0
    k_hyd_li_base = 10.0
    
    k_m_su_base = 30.0
    k_m_aa_base = 50.0
    k_m_fa_base = 6.0
    k_m_c4_base = 20.0
    k_m_pro_base = 13.0
    k_m_ac_base = 8.0
    k_m_h2_base = 35.0
    
    K_S_IN = 0.0001
    K_S_su = 0.5
    K_S_aa = 0.3
    K_S_fa = 0.4
    K_S_c4 = 0.2
    K_S_pro = 0.1
    K_S_ac = 0.15
    K_S_h2 = 7e-06
    
    K_I_h2_fa = 5e-06
    K_I_h2_c4 = 1e-05
    K_I_h2_pro = 3.5e-06
    K_I_nh3 = 0.0018
    
    k_dec_all = 0.02

    # Inhibition pH Bounds
    pH_LL_aa = 4.0
    pH_UL_aa = 5.5
    pH_LL_ac = 6.0
    pH_UL_ac = 7.0
    pH_LL_h2 = 5.0
    pH_UL_h2 = 6.0

    K_pH_aa = 10**-((pH_LL_aa + pH_UL_aa)/2.0)
    nn_aa = 3.0/(pH_UL_aa - pH_LL_aa)
    K_pH_ac = 10**-((pH_LL_ac + pH_UL_ac)/2.0)
    n_ac = 3.0/(pH_UL_ac - pH_LL_ac)
    K_pH_h2 = 10**-((pH_LL_h2 + pH_UL_h2)/2.0)
    n_h2 = 3.0/(pH_UL_h2 - pH_LL_h2)
    
    K_a_va = 10**-4.86
    K_a_bu = 10**-4.82
    K_a_pro = 10**-4.88
    K_a_ac = 10**-4.76

    # --- 4. STATE INITIALIZATION ---
    y0 = np.zeros(38)
    initial_cols = [
        "S_su", "S_aa", "S_fa", "S_va", "S_bu", "S_pro", "S_ac", "S_h2", "S_ch4", 
        "S_IC", "S_IN", "S_I", "X_xc", "X_ch", "X_pr", "X_li", "X_su", "X_aa", 
        "X_fa", "X_c4", "X_pro", "X_ac", "X_h2", "X_I", "S_cation", "S_anion", 
        "S_H_ion", "S_va_ion", "S_bu_ion", "S_pro_ion", "S_ac_ion", "S_hco3_ion", 
        "S_co2", "S_nh3", "S_nh4_ion", "S_gas_h2", "S_gas_ch4", "S_gas_co2"
    ]
    for idx, col in enumerate(initial_cols):
        if col in initial_df.columns:
            y0[idx] = initial_df[col][0]

    # --- 5. THE ODE ENGINE ---
    def ADM1_ODE(t, y, s_in_raw, T_c):
        T_k = T_c + 273.15
        alpha_T = get_ctm_multiplier(T_c)
        
        # Van't Hoff dynamic corrections
        K_w_dyn = 10**-14.0 * np.exp((55900/(100*R)) * (1/T_base - 1/T_k))
        K_a_co2_dyn = 10**-6.35 * np.exp((7646/(100*R)) * (1/T_base - 1/T_k))
        K_a_IN_dyn = 10**-9.25 * np.exp((51965/(100*R)) * (1/T_base - 1/T_k))
        K_H_co2_dyn = 0.035 * np.exp((-19410/(100*R))* (1/T_base - 1/T_k))
        K_H_ch4_dyn = 0.0014 * np.exp((-14240/(100*R)) * (1/T_base - 1/T_k))
        K_H_h2_dyn = 7.8e-04 * np.exp(-4180/(100*R) * (1/T_base - 1/T_k))
        p_g_h2o_dyn = 0.0313 * np.exp(5290 * (1/T_base - 1/T_k))

        # Dynamic Rates
        k_dis = k_dis_base * alpha_T
        k_hyd_ch = k_hyd_ch_base * alpha_T
        k_hyd_pr = k_hyd_pr_base * alpha_T
        k_hyd_li = k_hyd_li_base * alpha_T
        
        k_m_su = k_m_su_base * alpha_T
        k_m_aa = k_m_aa_base * alpha_T
        k_m_fa = k_m_fa_base * alpha_T
        k_m_c4 = k_m_c4_base * alpha_T
        k_m_pro = k_m_pro_base * alpha_T
        k_m_ac = k_m_ac_base * alpha_T
        k_m_h2 = k_m_h2_base * alpha_T
        
        # Unpack Influent & State
        inf = np.array(s_in_raw)
        for i in [0, 1, 2, 12, 13, 14, 15]: inf[i] *= load_factor
        
        S_su_in, S_aa_in, S_fa_in, S_va_in, S_bu_in, S_pro_in, S_ac_in, S_h2_in, S_ch4_in, S_IC_in, S_IN_in, S_I_in, X_xc_in, X_ch_in, X_pr_in, X_li_in, X_su_in, X_aa_in, X_fa_in, X_c4_in, X_pro_in, X_ac_in, X_h2_in, X_I_in, S_cat_in, S_ani_in = inf
        S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I, X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I, S_cat, S_ani, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_co2, S_nh3, S_nh4_ion, S_gas_h2, S_gas_ch4, S_gas_co2 = y

        # Inhibition
        I_pH_aa = (K_pH_aa**nn_aa)/(S_H_ion**nn_aa + K_pH_aa**nn_aa)
        I_pH_ac = (K_pH_ac**n_ac)/(S_H_ion**n_ac + K_pH_ac**n_ac)
        I_pH_h2 = (K_pH_h2**n_h2)/(S_H_ion**n_h2 + K_pH_h2**n_h2)
        I_IN_lim = 1/(1+(K_S_IN/S_IN))
        I_h2_fa = 1/(1+(S_h2/K_I_h2_fa))
        I_h2_c4 = 1/(1+(S_h2/K_I_h2_c4))
        I_h2_pro = 1/(1+(S_h2/K_I_h2_pro))
        I_nh3 = 1/(1+(S_nh3/K_I_nh3))

        # 19 Process Rates (Rho)
        Rho0 = k_dis * X_xc
        Rho1 = k_hyd_ch * X_ch
        Rho2 = k_hyd_pr * X_pr
        Rho3 = k_hyd_li * X_li
        Rho4 = k_m_su * (S_su/(K_S_su + S_su)) * X_su * I_pH_aa * I_IN_lim
        Rho5 = k_m_aa * (S_aa/(K_S_aa + S_aa)) * X_aa * I_pH_aa * I_IN_lim
        Rho6 = k_m_fa * (S_fa/(K_S_fa + S_fa)) * X_fa * I_pH_aa * I_IN_lim * I_h2_fa
        Rho7 = k_m_c4 * (S_va/(K_S_c4 + S_va)) * X_c4 * (S_va/(S_va+S_bu+1e-7)) * I_pH_aa * I_IN_lim * I_h2_c4
        Rho8 = k_m_c4 * (S_bu/(K_S_c4 + S_bu)) * X_c4 * (S_bu/(S_va+S_bu+1e-7)) * I_pH_aa * I_IN_lim * I_h2_c4
        Rho9 = k_m_pro * (S_pro/(K_S_pro + S_pro)) * X_pro * I_pH_aa * I_IN_lim * I_h2_pro
        Rho10 = k_m_ac * (S_ac/(K_S_ac + S_ac)) * X_ac * I_pH_ac * I_IN_lim * I_nh3
        Rho11 = k_m_h2 * (S_h2/(K_S_h2 + S_h2)) * X_h2 * I_pH_h2 * I_IN_lim
        Rho12 = k_dec_all * X_su
        Rho13 = k_dec_all * X_aa
        Rho14 = k_dec_all * X_fa
        Rho15 = k_dec_all * X_c4
        Rho16 = k_dec_all * X_pro
        Rho17 = k_dec_all * X_ac
        Rho18 = k_dec_all * X_h2

        # Gas Transfer
        p_g_h2 = (S_gas_h2 * R * T_k / 16.0)
        p_g_ch4 = (S_gas_ch4 * R * T_k / 64.0)
        p_g_co2 = (S_gas_co2 * R * T_k)
        p_gas_total = p_g_h2 + p_g_ch4 + p_g_co2 + p_g_h2o_dyn
        q_gas = k_p * (p_gas_total - p_atm) if p_gas_total > p_atm else 0.0
        
        Rho_T8 = k_La * (S_h2 - 16.0 * K_H_h2_dyn * p_g_h2)
        Rho_T9 = k_La * (S_ch4 - 64.0 * K_H_ch4_dyn * p_g_ch4)
        Rho_T10 = k_La * (S_co2 - K_H_co2_dyn * p_g_co2)

        # Stoichiometry Sigma
        s1 = (-1*C_xc + f_sI_xc*C_sI + f_ch_xc*C_ch + f_pr_xc*C_pr + f_li_xc*C_li + f_xI_xc*C_xI)
        s5 = (-1*C_su + (1-Y_su)*(f_bu_su*C_bu + f_pro_su*C_pro + f_ac_su*C_ac) + Y_su*C_bac)
        s6 = (-1*C_aa + (1-Y_aa)*(f_va_aa*C_va + f_bu_aa*C_bu + f_pro_aa*C_pro + f_ac_aa*C_ac) + Y_aa*C_bac)
        s7 = (-1*C_fa + (1-Y_fa)*0.7*C_ac + Y_fa*C_bac)
        s8 = (-1*C_va + (1-Y_c4)*0.54*C_pro + (1-Y_c4)*0.31*C_ac + Y_c4*C_bac)
        s9 = (-1*C_bu + (1-Y_c4)*0.8*C_ac + Y_c4*C_bac)
        s10 = (-1*C_pro + (1-Y_pro)*0.57*C_ac + Y_pro*C_bac)
        s11 = (-1*C_ac + (1-Y_ac)*C_ch4 + Y_ac*C_bac)
        s12 = ((1-Y_h2)*C_ch4 + Y_h2*C_bac)
        Sigma = s1*Rho0 + s5*Rho4 + s6*Rho5 + s7*Rho6 + s8*Rho7 + s9*Rho8 + s10*Rho9 + s11*Rho10 + s12*Rho11 + (-1*C_bac+C_xc)*(Rho12+Rho13+Rho14+Rho15+Rho16+Rho17+Rho18)

        # 38 Differentials
        dy = np.zeros(38)
        dy[0] = q_ad_standard/V_liq*(S_su_in-S_su) + Rho1 + (1-f_fa_li)*Rho3 - Rho4
        dy[1] = q_ad_standard/V_liq*(S_aa_in-S_aa) + Rho2 - Rho5
        dy[2] = q_ad_standard/V_liq*(S_fa_in-S_fa) + f_fa_li*Rho3 - Rho6
        dy[3] = q_ad_standard/V_liq*(S_va_in-S_va) + (1-Y_aa)*f_va_aa*Rho5 - Rho7
        dy[4] = q_ad_standard/V_liq*(S_bu_in-S_bu) + (1-Y_su)*f_bu_su*Rho4 + (1-Y_aa)*f_bu_aa*Rho5 - Rho8
        dy[5] = q_ad_standard/V_liq*(S_pro_in-S_pro) + (1-Y_su)*f_pro_su*Rho4 + (1-Y_aa)*f_pro_aa*Rho5 + (1-Y_c4)*0.54*Rho7 - Rho9
        dy[6] = q_ad_standard/V_liq*(S_ac_in-S_ac) + (1-Y_su)*f_ac_su*Rho4 + (1-Y_aa)*f_ac_aa*Rho5 + (1-Y_fa)*0.7*Rho6 + (1-Y_c4)*0.31*Rho7 + (1-Y_c4)*0.8*Rho8 + (1-Y_pro)*0.57*Rho9 - Rho10
        dy[8] = q_ad_standard/V_liq*(S_ch4_in-S_ch4) + (1-Y_ac)*Rho10 + (1-Y_h2)*Rho11 - Rho_T9
        dy[9] = q_ad_standard/V_liq*(S_IC_in-S_IC) - Sigma - Rho_T10
        dy[10] = q_ad_standard/V_liq*(S_IN_in-S_IN) + (N_xc-f_xI_xc*N_I-f_sI_xc*N_I-f_pr_xc*N_aa)*Rho0 - Y_su*N_bac*Rho4 + (N_aa-Y_aa*N_bac)*Rho5 - (Y_fa+Y_c4+Y_c4+Y_pro+Y_ac+Y_h2)*N_bac*(Rho6+Rho7+Rho8+Rho9+Rho10+Rho11) + (N_bac-N_xc)*(Rho12+Rho13+Rho14+Rho15+Rho16+Rho17+Rho18)
        dy[11] = q_ad_standard/V_liq*(S_I_in-S_I) + f_sI_xc*Rho0
        dy[12] = q_ad_standard/V_liq*(X_xc_in-X_xc) - Rho0 + (Rho12+Rho13+Rho14+Rho15+Rho16+Rho17+Rho18)
        dy[13] = q_ad_standard/V_liq*(X_ch_in-X_ch) + f_ch_xc*Rho0 - Rho1
        dy[14] = q_ad_standard/V_liq*(X_pr_in-X_pr) + f_pr_xc*Rho0 - Rho2
        dy[15] = q_ad_standard/V_liq*(X_li_in-X_li) + f_li_xc*Rho0 - Rho3
        dy[16] = q_ad_standard/V_liq*(X_su_in-X_su) + Y_su*Rho4 - Rho12
        dy[17] = q_ad_standard/V_liq*(X_aa_in-X_aa) + Y_aa*Rho5 - Rho13
        dy[18] = q_ad_standard/V_liq*(X_fa_in-X_fa) + Y_fa*Rho6 - Rho14
        dy[19] = q_ad_standard/V_liq*(X_c4_in-X_c4) + Y_c4*Rho7 + Y_c4*Rho8 - Rho15
        dy[20] = q_ad_standard/V_liq*(X_pro_in-X_pro) + Y_pro*Rho9 - Rho16
        dy[21] = q_ad_standard/V_liq*(X_ac_in-X_ac) + Y_ac*Rho10 - Rho17
        dy[22] = q_ad_standard/V_liq*(X_h2_in-X_h2) + Y_h2*Rho11 - Rho18
        dy[23] = q_ad_standard/V_liq*(X_I_in-X_I) + f_xI_xc*Rho0
        dy[24] = q_ad_standard/V_liq*(S_cat_in-S_cat)
        dy[25] = q_ad_standard/V_liq*(S_ani_in-S_ani)
        dy[35] = (q_gas/V_gas*-1*S_gas_h2) + (Rho_T8*V_liq/V_gas)
        dy[36] = (q_gas/V_gas*-1*S_gas_ch4) + (Rho_T9*V_liq/V_gas)
        dy[37] = (q_gas/V_gas*-1*S_gas_co2) + (Rho_T10*V_liq/V_gas)
        return dy

    def DAESolve(y, T_c):
        T_k = T_c + 273.15
        K_w_d = 10**-14.0 * np.exp((55900/(100*R)) * (1/T_base - 1/T_k))
        K_a_co2_d = 10**-6.35 * np.exp((7646/(100*R)) * (1/T_base - 1/T_k))
        K_a_IN_d = 10**-9.25 * np.exp((51965/(100*R)) * (1/T_base - 1/T_k))
        
        sh, it, max_it, tol = y[26], 0, 100, 1e-12
        while it < max_it:
            ac_i = K_a_ac*y[6]/(K_a_ac+sh)
            co2_i = K_a_co2_d*y[9]/(K_a_co2_d+sh)
            nh3 = K_a_IN_d*y[10]/(K_a_IN_d+sh)
            f = y[24] + (y[10]-nh3) + sh - co2_i - ac_i/64.0 - K_w_d/sh - y[25]
            df = 1 + K_a_IN_d*y[10]/(K_a_IN_d+sh)**2 + K_a_co2_d*y[9]/(K_a_co2_d+sh)**2 + K_w_d/sh**2
            sh = sh - f/df
            if abs(f) < tol: break
            it += 1
        y[26] = max(sh, 1e-12)
        y[30], y[31], y[33] = K_a_ac*y[6]/(K_a_ac+sh), K_a_co2_d*y[9]/(K_a_co2_d+sh), K_a_IN_d*y[10]/(K_a_IN_d+sh)
        return y

    # --- 6. MAIN RUN LOOP ---
    t_vals = influent_df['time'].values
    y_curr, sim_data = y0, []
    
    for i in range(len(t_vals)-1):
        T_step = influent_df['temp'].iloc[i] 
        s_in = influent_df.iloc[i][1:27].values
        
        sol = scipy.integrate.solve_ivp(ADM1_ODE, [t_vals[i], t_vals[i+1]], y_curr, args=(s_in, T_step), method='DOP853')
        y_curr = DAESolve(sol.y[:, -1], T_step)
        
        if i % 4 == 0: 
            res_row = y_curr.tolist() + [-np.log10(max(y_curr[26], 1e-12)), t_vals[i], T_step]
            sim_data.append(res_row)

    cols = initial_cols + ["pH", "time", "operating_temp"]
    return pd.DataFrame(sim_data, columns=cols)