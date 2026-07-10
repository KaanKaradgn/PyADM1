import numpy as np
import scipy.integrate
import copy
import pandas as pd
import random

# Global değişkenlerin tanımlanması
S_su_in=S_aa_in=S_fa_in=S_va_in=S_bu_in=S_pro_in=S_ac_in=S_h2_in=S_ch4_in=S_IC_in=S_IN_in=S_I_in=0
X_xc_in=X_ch_in=X_pr_in=X_li_in=X_su_in=X_aa_in=X_fa_in=X_c4_in=X_pro_in=X_ac_in=X_h2_in=X_I_in=0
S_cation_in=S_anion_in=0

S_va_ion=S_bu_ion=S_pro_ion=S_ac_ion=S_hco3_ion=S_nh3=S_H_ion=pH=p_gas_h2=S_h2=S_nh4_ion=S_co2=0
P_gas=q_gas=q_ch4=0

state_input = []
influent_state = None
initial_state = None

# TEMPERATURE LOGIC: Cardinal Temperature Model (CTM)
def get_ctm_multiplier(T, T_min=15.0, T_opt=37.0, T_max=44.0, T_ref=35.0):
    if T <= T_min or T >= T_max:
        return 0.0
    def ctm_core(t_val):
        numerator = (t_val - T_max) * ((t_val - T_min) ** 2)
        denominator = (T_opt - T_min) * ((T_opt - T_min) * (t_val - T_opt) - (T_opt - T_max) * (T_opt + T_min - 2 * t_val))
        return numerator / denominator
    ctm_current = ctm_core(T)
    ctm_ref = ctm_core(T_ref)
    return ctm_current / ctm_ref

def setInfluent(i):
    global S_su_in, S_aa_in, S_fa_in, S_va_in, S_bu_in, S_pro_in, S_ac_in, S_h2_in,S_ch4_in, S_IC_in, S_IN_in, S_I_in,X_xc_in, X_ch_in,X_pr_in,X_li_in,X_su_in,X_aa_in,X_fa_in,X_c4_in,X_pro_in,X_ac_in,X_h2_in,X_I_in,S_cation_in,S_anion_in
    global influent_state
    
    S_su_in = influent_state['S_su'][i] 
    S_aa_in = influent_state['S_aa'][i] 
    S_fa_in = influent_state['S_fa'][i] 
    S_va_in = influent_state['S_va'][i] 
    S_bu_in = influent_state['S_bu'][i] 
    S_pro_in = influent_state['S_pro'][i] 
    S_ac_in = influent_state['S_ac'][i] 
    S_h2_in = influent_state['S_h2'][i] 
    S_ch4_in = influent_state['S_ch4'][i]  
    S_IC_in = influent_state['S_IC'][i] 
    S_IN_in = influent_state['S_IN'][i] 
    S_I_in = influent_state['S_I'][i] 
    
    X_xc_in = influent_state['X_xc'][i] 
    X_ch_in = influent_state['X_ch'][i] 
    X_pr_in = influent_state['X_pr'][i] 
    X_li_in = influent_state['X_li'][i] 
    X_su_in = influent_state['X_su'][i] 
    X_aa_in = influent_state['X_aa'][i] 
    X_fa_in = influent_state['X_fa'][i] 
    X_c4_in = influent_state['X_c4'][i] 
    X_pro_in = influent_state['X_pro'][i] 
    X_ac_in = influent_state['X_ac'][i] 
    X_h2_in = influent_state['X_h2'][i] 
    X_I_in = influent_state['X_I'][i] 
    
    S_cation_in = influent_state['S_cation'][i] 
    S_anion_in = influent_state['S_anion'][i] 

def ADM1_ODE(t, state_zero):
  global S_nh4_ion, S_co2, p_gas, q_gas, q_ch4, state_input
  global k_dis, k_hyd_ch, k_hyd_pr, k_hyd_li, k_m_su, K_S_su, k_m_aa, K_S_aa, k_m_fa, K_S_fa, K_I_h2_fa, k_m_c4, K_S_c4, K_I_h2_c4, k_m_pro, K_S_pro, K_I_h2_pro, k_m_ac, K_S_ac, K_I_nh3, k_m_h2, K_S_h2, k_dec_X_su, k_dec_X_aa, k_dec_X_fa, k_dec_X_c4, k_dec_X_pro, k_dec_X_ac, k_dec_X_h2
  global f_sI_xc, f_xI_xc, f_ch_xc, f_pr_xc, f_li_xc, N_xc, N_I, N_aa, C_xc, C_sI, C_ch, C_pr, C_li, C_xI, C_su, C_aa, f_fa_li, C_fa, f_h2_su, f_bu_su, f_pro_su, f_ac_su, N_bac, C_bu, C_pro, C_ac, C_bac, Y_su, f_h2_aa, f_va_aa, f_bu_aa, f_pro_aa, f_ac_aa, C_va, Y_aa, Y_fa, Y_c4, Y_pro, C_ch4, Y_ac, Y_h2
  global R, T_op, K_w, K_a_va, K_a_bu, K_a_pro, K_a_ac, K_a_co2, K_a_IN, k_A_B_va, k_A_B_bu, k_A_B_pro, k_A_B_ac, k_A_B_co2, k_A_B_IN, p_gas_h2o, k_p, k_L_a, K_H_co2, K_H_ch4, K_H_h2, V_liq, V_gas, q_ad, p_atm
  global K_pH_aa, nn_aa, K_pH_ac, n_ac, K_pH_h2, n_h2, K_S_IN
  global T_step_curr, q_ad_dynamic # Dynamic inputs from loop

  S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I, X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I, S_cation, S_anion, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_co2_state, S_nh3_state, S_nh4_ion_state, S_gas_h2, S_gas_ch4, S_gas_co2 = state_zero

  S_su_in, S_aa_in, S_fa_in, S_va_in, S_bu_in, S_pro_in, S_ac_in, S_h2_in, S_ch4_in, S_IC_in, S_IN_in, S_I_in, X_xc_in, X_ch_in, X_pr_in, X_li_in, X_su_in, X_aa_in, X_fa_in, X_c4_in, X_pro_in, X_ac_in, X_h2_in, X_I_in, S_cation_in, S_anion_in = state_input

  # TEMPERATURE AND THERMODYNAMIC CALCULATIONS (DYNAMIC)
  T_base = 298.15
  T_k_curr = T_step_curr + 273.15
  alpha_T = get_ctm_multiplier(T_step_curr)

  K_w_d = 10 ** -14.0 * np.exp((55900 / (100 * R)) * (1 / T_base - 1 / T_k_curr))
  K_a_co2_d = 10 ** -6.35 * np.exp((7646 / (100 * R)) * (1 / T_base - 1 / T_k_curr))
  K_a_IN_d = 10 ** -9.25 * np.exp((51965 / (100 * R)) * (1 / T_base - 1 / T_k_curr))
  K_H_co2_d = 0.035 * np.exp((-19410 / (100 * R)) * (1 / T_base - 1 / T_k_curr))
  K_H_ch4_d = 0.0014 * np.exp((-14240 / (100 * R)) * (1 / T_base - 1 / T_k_curr))
  K_H_h2_d = 7.8 * 10 ** -4 * np.exp(-4180 / (100 * R) * (1 / T_base - 1 / T_k_curr))
  p_gas_h2o_d = 0.0313 * np.exp(5290 * (1 / T_base - 1 / T_k_curr))

  # DYNAMIC KINETICS
  k_dis_d = k_dis * alpha_T
  k_hyd_ch_d = k_hyd_ch * alpha_T
  k_hyd_pr_d = k_hyd_pr * alpha_T
  k_hyd_li_d = k_hyd_li * alpha_T
  k_m_su_d = k_m_su * alpha_T
  k_m_aa_d = k_m_aa * alpha_T
  k_m_fa_d = k_m_fa * alpha_T
  k_m_c4_d = k_m_c4 * alpha_T
  k_m_pro_d = k_m_pro * alpha_T
  k_m_ac_d = k_m_ac * alpha_T
  k_m_h2_d = k_m_h2 * alpha_T

  S_nh4_ion =  (S_IN - S_nh3_state)
  S_co2 =  (S_IC - S_hco3_ion)

  I_pH_aa =  ((K_pH_aa ** nn_aa) / (S_H_ion ** nn_aa + K_pH_aa ** nn_aa))
  I_pH_ac =  ((K_pH_ac ** n_ac) / (S_H_ion ** n_ac + K_pH_ac ** n_ac))
  I_pH_h2 =  ((K_pH_h2 ** n_h2) / (S_H_ion ** n_h2 + K_pH_h2 ** n_h2))
  I_IN_lim =  (1 / (1 + (K_S_IN / S_IN)))
  I_h2_fa =  (1 / (1 + (S_h2 / K_I_h2_fa)))
  I_h2_c4 =  (1 / (1 + (S_h2 / K_I_h2_c4)))
  I_h2_pro =  (1 / (1 + (S_h2 / K_I_h2_pro)))
  I_nh3 =  (1 / (1 + (S_nh3_state / K_I_nh3)))

  I_5 =  (I_pH_aa * I_IN_lim)
  I_6 = I_5
  I_7 =  (I_pH_aa * I_IN_lim * I_h2_fa)
  I_8 =  (I_pH_aa * I_IN_lim * I_h2_c4)
  I_9 = I_8
  I_10 =  (I_pH_aa * I_IN_lim * I_h2_pro)
  I_11 =  (I_pH_ac * I_IN_lim * I_nh3)
  I_12 =  (I_pH_h2 * I_IN_lim)

  # biochemical process rates with dynamic kinetics
  Rho_1 =  (k_dis_d * X_xc)   
  Rho_2 =  (k_hyd_ch_d * X_ch)  
  Rho_3 =  (k_hyd_pr_d * X_pr)  
  Rho_4 =  (k_hyd_li_d * X_li)  
  Rho_5 =  k_m_su_d * S_su / (K_S_su + S_su) * X_su * I_5  
  Rho_6 =  (k_m_aa_d * (S_aa / (K_S_aa + S_aa)) * X_aa * I_6)  
  Rho_7 =  (k_m_fa_d * (S_fa / (K_S_fa + S_fa)) * X_fa * I_7)  
  Rho_8 =  (k_m_c4_d * (S_va / (K_S_c4 + S_va )) * X_c4 * (S_va / (S_bu + S_va + 1e-6)) * I_8)  
  Rho_9 =  (k_m_c4_d * (S_bu / (K_S_c4 + S_bu )) * X_c4 * (S_bu / (S_bu + S_va + 1e-6)) * I_9)  
  Rho_10 =  (k_m_pro_d * (S_pro / (K_S_pro + S_pro)) * X_pro * I_10)  
  Rho_11 =  (k_m_ac_d * (S_ac / (K_S_ac + S_ac)) * X_ac * I_11)  
  Rho_12 =  (k_m_h2_d * (S_h2 / (K_S_h2 + S_h2)) * X_h2 * I_12)  
  Rho_13 =  (k_dec_X_su * X_su)  
  Rho_14 =  (k_dec_X_aa * X_aa)  
  Rho_15 =  (k_dec_X_fa * X_fa)  
  Rho_16 =  (k_dec_X_c4 * X_c4)  
  Rho_17 =  (k_dec_X_pro * X_pro)  
  Rho_18 =  (k_dec_X_ac * X_ac)  
  Rho_19 =  (k_dec_X_h2 * X_h2)  

  Rho_A_4 =  (k_A_B_va * (S_va_ion * (K_a_va + S_H_ion) - K_a_va * S_va))
  Rho_A_5 =  (k_A_B_bu * (S_bu_ion * (K_a_bu + S_H_ion) - K_a_bu * S_bu))
  Rho_A_6 =  (k_A_B_pro * (S_pro_ion * (K_a_pro + S_H_ion) - K_a_pro * S_pro))
  Rho_A_7 =  (k_A_B_ac * (S_ac_ion * (K_a_ac + S_H_ion) - K_a_ac * S_ac))
  Rho_A_10 =  (k_A_B_co2 * (S_hco3_ion * (K_a_co2_d + S_H_ion) - K_a_co2_d * S_IC))
  Rho_A_11 =  (k_A_B_IN * (S_nh3_state * (K_a_IN_d + S_H_ion) - K_a_IN_d * S_IN))

  p_gas_h2 =  (S_gas_h2 * R * T_k_curr / 16)
  p_gas_ch4 =  (S_gas_ch4 * R * T_k_curr / 64)
  p_gas_co2 =  (S_gas_co2 * R * T_k_curr)
  p_gas = (p_gas_h2 + p_gas_ch4 + p_gas_co2 + p_gas_h2o_d)
  
  q_gas =  (k_p * (p_gas - p_atm))
  if q_gas < 0:    q_gas = 0

  q_ch4 = q_gas * (p_gas_ch4/p_gas) if p_gas > 0 else 0

  Rho_T_8 =  (k_L_a * (S_h2 - 16 * K_H_h2_d * p_gas_h2))
  Rho_T_9 =  (k_L_a * (S_ch4 - 64 * K_H_ch4_d * p_gas_ch4))
  Rho_T_10 =  (k_L_a * (S_co2_state - K_H_co2_d * p_gas_co2))

  # HRT Calculation within differentials using global q_ad_dynamic
  diff_S_su = q_ad_dynamic / V_liq * (S_su_in - S_su) + Rho_2 + (1 - f_fa_li) * Rho_4 - Rho_5 
  diff_S_aa = q_ad_dynamic / V_liq * (S_aa_in - S_aa) + Rho_3 - Rho_6  
  diff_S_fa = q_ad_dynamic / V_liq * (S_fa_in - S_fa) + (f_fa_li * Rho_4) - Rho_7  
  diff_S_va = q_ad_dynamic / V_liq * (S_va_in - S_va) + (1 - Y_aa) * f_va_aa * Rho_6 - Rho_8  
  diff_S_bu = q_ad_dynamic / V_liq * (S_bu_in - S_bu) + (1 - Y_su) * f_bu_su * Rho_5 + (1 - Y_aa) * f_bu_aa * Rho_6 - Rho_9  
  diff_S_pro = q_ad_dynamic / V_liq * (S_pro_in - S_pro) + (1 - Y_su) * f_pro_su * Rho_5 + (1 - Y_aa) * f_pro_aa * Rho_6 + (1 - Y_c4) * 0.54 * Rho_8 - Rho_10 
  diff_S_ac = q_ad_dynamic / V_liq * (S_ac_in - S_ac) + (1 - Y_su) * f_ac_su * Rho_5 + (1 - Y_aa) * f_ac_aa * Rho_6 + (1 - Y_fa) * 0.7 * Rho_7 + (1 - Y_c4) * 0.31 * Rho_8 + (1 - Y_c4) * 0.8 * Rho_9 + (1 - Y_pro) * 0.57 * Rho_10 - Rho_11  
  diff_S_ch4 = q_ad_dynamic / V_liq * (S_ch4_in - S_ch4) + (1 - Y_ac) * Rho_11 + (1 - Y_h2) * Rho_12 - Rho_T_9  

  s_1 =  (-1 * C_xc + f_sI_xc * C_sI + f_ch_xc * C_ch + f_pr_xc * C_pr + f_li_xc * C_li + f_xI_xc * C_xI) 
  s_2 =  (-1 * C_ch + C_su)
  s_3 =  (-1 * C_pr + C_aa)
  s_4 =  (-1 * C_li + (1 - f_fa_li) * C_su + f_fa_li * C_fa)
  s_5 =  (-1 * C_su + (1 - Y_su) * (f_bu_su * C_bu + f_pro_su * C_pro + f_ac_su * C_ac) + Y_su * C_bac)
  s_6 =  (-1 * C_aa + (1 - Y_aa) * (f_va_aa * C_va + f_bu_aa * C_bu + f_pro_aa * C_pro + f_ac_aa * C_ac) + Y_aa * C_bac)
  s_7 =  (-1 * C_fa + (1 - Y_fa) * 0.7 * C_ac + Y_fa * C_bac)
  s_8 =  (-1 * C_va + (1 - Y_c4) * 0.54 * C_pro + (1 - Y_c4) * 0.31 * C_ac + Y_c4 * C_bac)
  s_9 =  (-1 * C_bu + (1 - Y_c4) * 0.8 * C_ac + Y_c4 * C_bac)
  s_10 =  (-1 * C_pro + (1 - Y_pro) * 0.57 * C_ac + Y_pro * C_bac)
  s_11 =  (-1 * C_ac + (1 - Y_ac) * C_ch4 + Y_ac * C_bac)
  s_12 =  ((1 - Y_h2) * C_ch4 + Y_h2 * C_bac)
  s_13 =  (-1 * C_bac + C_xc) 

  Sigma =  (s_1 * Rho_1 + s_2 * Rho_2 + s_3 * Rho_3 + s_4 * Rho_4 + s_5 * Rho_5 + s_6 * Rho_6 + s_7 * Rho_7 + s_8 * Rho_8 + s_9 * Rho_9 + s_10 * Rho_10 + s_11 * Rho_11 + s_12 * Rho_12 + s_13 * (Rho_13 + Rho_14 + Rho_15 + Rho_16 + Rho_17 + Rho_18 + Rho_19))

  diff_S_IC = q_ad_dynamic / V_liq * (S_IC_in - S_IC) - Sigma - Rho_T_10
  diff_S_IN = q_ad_dynamic / V_liq * (S_IN_in - S_IN) + (N_xc - f_xI_xc * N_I - f_sI_xc * N_I-f_pr_xc * N_aa) * Rho_1 - Y_su * N_bac * Rho_5 + (N_aa - Y_aa * N_bac) * Rho_6 - Y_fa * N_bac * Rho_7 - Y_c4 * N_bac * Rho_8 - Y_c4 * N_bac * Rho_9 - Y_pro * N_bac * Rho_10 - Y_ac * N_bac * Rho_11 - Y_h2 * N_bac * Rho_12 + (N_bac - N_xc) * (Rho_13 + Rho_14 + Rho_15 + Rho_16 + Rho_17 + Rho_18 + Rho_19) 
  diff_S_I = q_ad_dynamic / V_liq * (S_I_in - S_I) + f_sI_xc * Rho_1  
  diff_X_xc = q_ad_dynamic / V_liq * (X_xc_in - X_xc) - Rho_1 + Rho_13 + Rho_14 + Rho_15 + Rho_16 + Rho_17 + Rho_18 + Rho_19  
  diff_X_ch = q_ad_dynamic / V_liq * (X_ch_in - X_ch) + f_ch_xc * Rho_1 - Rho_2 
  diff_X_pr = q_ad_dynamic / V_liq * (X_pr_in - X_pr) + f_pr_xc * Rho_1 - Rho_3 
  diff_X_li = q_ad_dynamic / V_liq * (X_li_in - X_li) + f_li_xc * Rho_1 - Rho_4  
  diff_X_su = q_ad_dynamic / V_liq * (X_su_in - X_su) + Y_su * Rho_5 - Rho_13 
  diff_X_aa = q_ad_dynamic / V_liq * (X_aa_in - X_aa) + Y_aa * Rho_6 - Rho_14  
  diff_X_fa = q_ad_dynamic / V_liq * (X_fa_in - X_fa) + Y_fa * Rho_7 - Rho_15  
  diff_X_c4 = q_ad_dynamic / V_liq * (X_c4_in - X_c4) + Y_c4 * Rho_8 + Y_c4 * Rho_9 - Rho_16  
  diff_X_pro = q_ad_dynamic / V_liq * (X_pro_in - X_pro) + Y_pro * Rho_10 - Rho_17  
  diff_X_ac = q_ad_dynamic / V_liq * (X_ac_in - X_ac) + Y_ac * Rho_11 - Rho_18  
  diff_X_h2 = q_ad_dynamic / V_liq * (X_h2_in - X_h2) + Y_h2 * Rho_12 - Rho_19  
  diff_X_I = q_ad_dynamic / V_liq * (X_I_in - X_I) + f_xI_xc * Rho_1  
  diff_S_cation = q_ad_dynamic / V_liq * (S_cation_in - S_cation) 
  diff_S_anion = q_ad_dynamic / V_liq * (S_anion_in - S_anion)  
  diff_S_h2 = 0
  diff_S_va_ion = 0  
  diff_S_bu_ion = 0  
  diff_S_pro_ion = 0  
  diff_S_ac_ion = 0  
  diff_S_hco3_ion = 0  
  diff_S_nh3 = 0  
  diff_S_gas_h2 = (q_gas / V_gas * -1 * S_gas_h2) + (Rho_T_8 * V_liq / V_gas) 
  diff_S_gas_ch4 = (q_gas / V_gas * -1 * S_gas_ch4) + (Rho_T_9 * V_liq / V_gas)  
  diff_S_gas_co2 = (q_gas / V_gas * -1 * S_gas_co2) + (Rho_T_10 * V_liq / V_gas) 
  diff_S_H_ion = 0
  diff_S_co2 = 0
  diff_S_nh4_ion = 0 

  return diff_S_su, diff_S_aa, diff_S_fa, diff_S_va, diff_S_bu, diff_S_pro, diff_S_ac, diff_S_h2, diff_S_ch4, diff_S_IC, diff_S_IN, diff_S_I, diff_X_xc, diff_X_ch, diff_X_pr, diff_X_li, diff_X_su, diff_X_aa, diff_X_fa, diff_X_c4, diff_X_pro, diff_X_ac, diff_X_h2, diff_X_I, diff_S_cation, diff_S_anion, diff_S_H_ion, diff_S_va_ion,  diff_S_bu_ion, diff_S_pro_ion, diff_S_ac_ion, diff_S_hco3_ion, diff_S_co2,  diff_S_nh3, diff_S_nh4_ion, diff_S_gas_h2, diff_S_gas_ch4, diff_S_gas_co2

def simulate(t_step, state_zero, solvermethod):
  r = scipy.integrate.solve_ivp(ADM1_ODE, t_step, state_zero, method= solvermethod)
  return r.y

def DAESolve(S_va, S_bu, S_pro, S_ac, S_IC, S_IN, S_cation, S_anion, S_fa, S_h2_in, T_curr):
  global S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_nh3, S_H_ion, pH, p_gas_h2, S_h2, S_nh4_ion, S_co2, P_gas, q_gas
  global K_a_va, K_a_bu, K_a_pro, K_a_ac, K_a_co2, K_a_IN, K_w, K_pH_aa, nn_aa, K_pH_h2, n_h2, K_S_IN, K_I_h2_fa, K_I_h2_c4, K_I_h2_pro, k_m_su, K_S_su, X_su, k_m_aa, K_S_aa, X_aa, k_m_fa, K_S_fa, X_fa, k_m_c4, K_S_c4, X_c4, k_m_pro, K_S_pro, X_pro, k_m_h2, K_S_h2, X_h2, R, S_gas_h2, k_L_a, K_H_h2, q_ad, V_liq, Y_su, f_h2_su, Y_aa, f_h2_aa, Y_fa, Y_c4, Y_pro
  
  T_base = 298.15
  T_k = T_curr + 273.15
  K_w_d = 10**-14.0 * np.exp((55900/(100*R)) * (1/T_base - 1/T_k))
  K_a_co2_d = 10**-6.35 * np.exp((7646/(100*R)) * (1/T_base - 1/T_k))
  K_a_IN_d = 10**-9.25 * np.exp((51965/(100*R)) * (1/T_base - 1/T_k))

  eps = 0.0000001
  shdelta = 1.0
  shgradeq = 1.0
  tol = 10 ** (-12) 
  maxIter = 1000 
  i = 1
  
  while ((shdelta > tol or shdelta < -tol) and (i <= maxIter)):
    S_va_ion = K_a_va * S_va / (K_a_va + S_H_ion)
    S_bu_ion = K_a_bu * S_bu / (K_a_bu + S_H_ion)
    S_pro_ion = K_a_pro * S_pro / (K_a_pro + S_H_ion)
    S_ac_ion = K_a_ac * S_ac / (K_a_ac + S_H_ion)
    S_hco3_ion = K_a_co2_d * S_IC / (K_a_co2_d + S_H_ion)
    S_nh3 = K_a_IN_d * S_IN / (K_a_IN_d + S_H_ion)
    shdelta = S_cation + (S_IN - S_nh3) + S_H_ion - S_hco3_ion - S_ac_ion / 64.0 - S_pro_ion / 112.0 - S_bu_ion / 160.0 - S_va_ion / 208.0 - K_w_d / S_H_ion - S_anion
    shgradeq = 1 + K_a_IN_d * S_IN / ((K_a_IN_d + S_H_ion) ** 2) + K_a_co2_d * S_IC / ((K_a_co2_d + S_H_ion) ** 2) + 1 / 64.0 * K_a_ac * S_ac / ((K_a_ac + S_H_ion) ** 2) + 1 / 112.0 * K_a_pro * S_pro / ((K_a_pro + S_H_ion) ** 2) + 1 / 160.0 * K_a_bu * S_bu / ((K_a_bu + S_H_ion) ** 2) + 1 / 208.0 * K_a_va * S_va / ((K_a_va + S_H_ion) ** 2) + K_w_d / (S_H_ion ** 2)
    S_H_ion = S_H_ion - shdelta / shgradeq
    if S_H_ion <= 0:
        S_H_ion = tol
    i+=1
  pH = - np.log10(S_H_ion)
  return S_H_ion

def run_simulation(df_influent, df_initial, selected_params):
    global influent_state, initial_state, q_ad_dynamic, state_input, R, T_base, p_atm, V_liq, V_gas, T_step_curr
    global f_sI_xc, f_xI_xc, f_ch_xc, f_pr_xc, f_li_xc, k_dis, k_hyd_ch, k_hyd_pr, k_hyd_li
    global k_m_su, K_S_su, k_m_aa, K_S_aa, k_m_fa, K_S_fa, K_I_h2_fa, k_m_c4, K_S_c4, K_I_h2_c4, k_m_pro, K_S_pro, K_I_h2_pro, k_m_ac, K_S_ac, K_I_nh3, k_m_h2, K_S_h2
    global N_xc, N_I, N_aa, C_xc, C_sI, C_ch, C_pr, C_li, C_xI, C_su, C_aa, f_fa_li, C_fa, f_h2_su, f_bu_su, f_pro_su, f_ac_su, N_bac, C_bu, C_pro, C_ac, C_bac, Y_su, f_h2_aa, f_va_aa, f_bu_aa, f_pro_aa, f_ac_aa, C_va, Y_aa, Y_fa, Y_c4, Y_pro, C_ch4, Y_ac, Y_h2
    global K_S_IN, pH_UL_aa, pH_LL_aa, pH_UL_ac, pH_LL_ac, pH_UL_h2, pH_LL_h2, k_dec_X_su, k_dec_X_aa, k_dec_X_fa, k_dec_X_c4, k_dec_X_pro, k_dec_X_ac, k_dec_X_h2
    global K_pH_aa, nn_aa, K_pH_ac, n_ac, K_pH_h2, n_h2
    global K_w, K_a_va, K_a_bu, K_a_pro, K_a_ac, K_a_co2, K_a_IN, k_A_B_va, k_A_B_bu, k_A_B_pro, k_A_B_ac, k_A_B_co2, k_A_B_IN, p_gas_h2o, k_p, k_L_a, K_H_co2, K_H_ch4, K_H_h2
    global S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I, X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I, S_cation, S_anion, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_co2, S_nh3, S_nh4_ion, S_gas_h2, S_gas_ch4, S_gas_co2, pH

    influent_state = df_influent
    initial_state = df_initial

    R = 0.083145 
    T_base = 298.15 
    p_atm = 1.013 
    T_ad = 308.15 
    V_liq = 3400 
    V_gas = 300

    f_sI_xc = selected_params['stoich']['f_sI_xc']
    f_xI_xc = selected_params['stoich']['f_xI_xc']
    f_ch_xc = selected_params['stoich']['f_ch_xc']
    f_pr_xc = selected_params['stoich']['f_pr_xc']
    f_li_xc = selected_params['stoich']['f_li_xc']
    k_dis = selected_params['kinetics']['k_dis'] 
    k_hyd_ch = selected_params['kinetics']['k_hyd_ch'] 
    k_hyd_pr = selected_params['kinetics']['k_hyd_pr'] 
    k_hyd_li = selected_params['kinetics']['k_hyd_li'] 

    N_xc, N_I, N_aa, N_bac = 0.0376/14, 0.06/14, 0.007, 0.08/14
    C_xc, C_sI, C_ch, C_pr, C_li, C_xI, C_su, C_aa, C_fa, C_bu, C_pro, C_ac, C_bac, C_ch4, C_va = 0.02786, 0.03, 0.0313, 0.03, 0.022, 0.03, 0.0313, 0.03, 0.0217, 0.025, 0.0268, 0.0313, 0.0313, 0.0156, 0.024
    f_fa_li, f_h2_su, f_bu_su, f_pro_su, f_ac_su = 0.95, 0.19, 0.13, 0.27, 0.41
    f_h2_aa, f_va_aa, f_bu_aa, f_pro_aa, f_ac_aa = 0.06, 0.23, 0.26, 0.05, 0.40
    Y_su, Y_aa, Y_fa, Y_c4, Y_pro, Y_ac, Y_h2 = 0.1, 0.08, 0.06, 0.06, 0.04, 0.05, 0.06

    K_S_IN, k_m_su, K_S_su, k_m_aa, K_S_aa, k_m_fa, K_S_fa, K_I_h2_fa, k_m_c4, K_S_c4, K_I_h2_c4, k_m_pro, K_S_pro, K_I_h2_pro, k_m_ac, K_S_ac, K_I_nh3, k_m_h2, K_S_h2 = 10**-4, 30, 0.5, 50, 0.3, 6, 0.4, 5e-6, 20, 0.2, 1e-5, 13, 0.1, 3.5e-6, 8, 0.15, 0.0018, 35, 7e-6
    pH_UL_aa, pH_LL_aa, pH_UL_ac, pH_LL_ac, pH_UL_h2, pH_LL_h2 = 5.5, 4.0, 7.0, 6.0, 6.0, 5.0
    k_dec_X_su = k_dec_X_aa = k_dec_X_fa = k_dec_X_c4 = k_dec_X_pro = k_dec_X_ac = k_dec_X_h2 = 0.02

    K_w = 10**-14.0 * np.exp((55900/(100*R)) * (1/T_base - 1/T_ad)) 
    K_a_va, K_a_bu, K_a_pro, K_a_ac = 10**-4.86, 10**-4.82, 10**-4.88, 10**-4.76
    K_a_co2, K_a_IN = 10**-6.35 * np.exp((7646/(100*R)) * (1/T_base - 1/T_ad)), 10**-9.25 * np.exp((51965/(100*R)) * (1/T_base - 1/T_ad))
    k_A_B_va = k_A_B_bu = k_A_B_pro = k_A_B_ac = k_A_B_co2 = k_A_B_IN = 10**10 
    p_gas_h2o, k_p, k_L_a = 0.0313 * np.exp(5290 * (1 / T_base - 1 / T_ad)), 5e4, 200.0
    K_H_co2, K_H_ch4, K_H_h2 = 0.035 * np.exp((-19410/(100*R))* (1/T_base - 1/T_ad)), 0.0014 * np.exp((-14240/(100*R)) * (1/T_base - 1/T_ad)), 7.8e-4 * np.exp(-4180/(100*R) * (1/T_base - 1/T_ad))

    K_pH_aa = (10 ** (-1 * (pH_LL_aa + pH_UL_aa) / 2.0)); nn_aa = (3.0 / (pH_UL_aa - pH_LL_aa)) 
    K_pH_ac = (10 ** (-1 * (pH_LL_ac + pH_UL_ac) / 2.0)); n_ac = (3.0 / (pH_UL_ac - pH_LL_ac))
    K_pH_h2 = (10 ** (-1 * (pH_LL_h2 + pH_UL_h2) / 2.0)); n_h2 = (3.0 / (pH_UL_h2 - pH_LL_h2))

    S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I = initial_state['S_su'][0], initial_state['S_aa'][0], initial_state['S_fa'][0], initial_state['S_va'][0], initial_state['S_bu'][0], initial_state['S_pro'][0], initial_state['S_ac'][0], initial_state['S_h2'][0], initial_state['S_ch4'][0], initial_state['S_IC'][0], initial_state['S_IN'][0], initial_state['S_I'][0]
    X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I = initial_state['X_xc'][0], initial_state['X_ch'][0], initial_state['X_pr'][0], initial_state['X_li'][0], initial_state['X_su'][0], initial_state['X_aa'][0], initial_state['X_fa'][0], initial_state['X_c4'][0], initial_state['X_pro'][0], initial_state['X_ac'][0], initial_state['X_h2'][0], initial_state['X_I'][0]
    S_cation, S_anion, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_nh3, S_gas_h2, S_gas_ch4, S_gas_co2 = initial_state['S_cation'][0], initial_state['S_anion'][0], initial_state['S_H_ion'][0], initial_state['S_va_ion'][0], initial_state['S_bu_ion'][0], initial_state['S_pro_ion'][0], initial_state['S_ac_ion'][0], initial_state['S_hco3_ion'][0], initial_state['S_nh3'][0], initial_state['S_gas_h2'][0], initial_state['S_gas_ch4'][0], initial_state['S_gas_co2'][0]
    
    pH = - np.log10(S_H_ion)
    setInfluent(0) 
    
    state_zero = [S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I, X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I, S_cation, S_anion, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_co2, S_nh3, S_nh4_ion, S_gas_h2, S_gas_ch4, S_gas_co2]
    
    t = influent_state['time']
    simulate_results = pd.DataFrame([state_zero])
    columns = ["S_su", "S_aa", "S_fa", "S_va", "S_bu", "S_pro", "S_ac", "S_h2", "S_ch4", "S_IC", "S_IN", "S_I", "X_xc", "X_ch", "X_pr", "X_li", "X_su", "X_aa", "X_fa", "X_c4", "X_pro", "X_ac", "X_h2", "X_I", "S_cation", "S_anion", "S_H_ion", "S_va_ion", "S_bu_ion", "S_pro_ion", "S_ac_ion", "S_hco3_ion", "S_co2", "S_nh3", "S_nh4_ion", "S_gas_h2", "S_gas_ch4", "S_gas_co2"]
    simulate_results.columns = columns

    t0=0
    n=0
    for u in t[1:]:
        n+=1
        setInfluent(n)
        
        # DYNAMIC HRT & TEMPERATURE FROM CSV
        q_ad_dynamic = influent_state['q_ad'][n]
        T_step_curr = influent_state['temp'][n]

        # STOCHASTIC FEEDSTOCK VARIABILITY (+/- 5% wiggle)
        state_input = [S_su_in, S_aa_in, S_fa_in, S_va_in, S_bu_in, S_pro_in, S_ac_in, S_h2_in, S_ch4_in, S_IC_in, S_IN_in, S_I_in, X_xc_in, X_ch_in, X_pr_in, X_li_in, X_su_in, X_aa_in, X_fa_in, X_c4_in, X_pro_in, X_ac_in, X_h2_in, X_I_in, S_cation_in, S_anion_in]
        for organic_idx in [0, 1, 2, 12, 13, 14, 15]:
            state_input[organic_idx] *= random.uniform(0.95, 1.05)

        r_y = simulate([t0, u], state_zero, 'DOP853')
        
        S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I, X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I, S_cation, S_anion, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_co2, S_nh3, S_nh4_ion, S_gas_h2, S_gas_ch4, S_gas_co2 = [arr[-1] for arr in r_y]
        
        S_H_ion = DAESolve(S_va, S_bu, S_pro, S_ac, S_IC, S_IN, S_cation, S_anion, S_fa, S_h2, T_step_curr)

        state_zero = [S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_IC, S_IN, S_I, X_xc, X_ch, X_pr, X_li, X_su, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I, S_cation, S_anion, S_H_ion, S_va_ion, S_bu_ion, S_pro_ion, S_ac_ion, S_hco3_ion, S_co2, S_nh3, S_nh4_ion, S_gas_h2, S_gas_ch4, S_gas_co2]
        
        dfstate_zero = pd.DataFrame([state_zero], columns = columns)
        simulate_results = pd.concat([simulate_results, dfstate_zero], ignore_index=True)
        t0 = u

    simulate_results['pH'] = - np.log10(simulate_results['S_H_ion'])
    simulate_results.insert(0, 'time', t.values)
    return simulate_results