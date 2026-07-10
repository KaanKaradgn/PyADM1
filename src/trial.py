import pandas as pd


df1 = pd.read_excel("birinci_dosya.xlsx")
df2 = pd.read_excel("ikinci_dosya.xlsx")

sutun1 = df1["Sutun_X"]
sutun2 = df2["Sutun_Y"]

uzunluk1 = len(sutun1)
uzunluk2 = len(sutun2)

min_uzunluk = min(uzunluk1, uzunluk2)

sutun1_esit = sutun1.iloc[:min_uzunluk].reset_index(drop=True)
sutun2_esit = sutun2.iloc[:min_uzunluk].reset_index(drop=True)

korelasyon_pearson = sutun1_esit.corr(sutun2_esit)
print(f"Pearson Korelasyon Katsayısı : {korelasyon_pearson:.4f}")

