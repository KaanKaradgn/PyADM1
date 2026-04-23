import sys

class ADM1Simulator:
    """ADM1 Modeli için gübre spesifik konfigürasyon yöneticisi."""
    
    def __init__(self):
        self.manure_data = {
            "sigir": {
                "name": "Sığır Gübresi",
                "desc": "Yüksek lifli, düşük hidroliz hızı.",
                "kinetics": {"k_dis": 0.10, "k_hyd_ch": 0.25, "k_hyd_pr": 0.20, "k_hyd_li": 0.10},
                "stoich": {"f_ch_xc": 0.40, "f_pr_xc": 0.20, "f_li_xc": 0.05, "f_xI_xc": 0.25, "f_sI_xc": 0.10}
            },
            "domuz": {
                "name": "Domuz Gübresi",
                "desc": "Yüksek protein ve daha hızlı parçalanma.",
                "kinetics": {"k_dis": 0.25, "k_hyd_ch": 0.35, "k_hyd_pr": 0.40, "k_hyd_li": 0.20},
                "stoich": {"f_ch_xc": 0.30, "f_pr_xc": 0.30, "f_li_xc": 0.15, "f_xI_xc": 0.10, "f_sI_xc": 0.15}
            },
            "tavuk": {
                "name": "Tavuk Gübresi",
                "desc": "Çok yüksek protein ve amonyak riski.",
                "kinetics": {"k_dis": 0.30, "k_hyd_ch": 0.45, "k_hyd_pr": 0.55, "k_hyd_li": 0.30},
                "stoich": {"f_ch_xc": 0.20, "f_pr_xc": 0.50, "f_li_xc": 0.10, "f_xI_xc": 0.05, "f_sI_xc": 0.15}
            },
            "at": {
                "name": "At Gübresi",
                "desc": "Yüksek lignoselülozik yapı, yavaş parçalanma.",
                "kinetics": {"k_dis": 0.06, "k_hyd_ch": 0.12, "k_hyd_pr": 0.15, "k_hyd_li": 0.08},
                "stoich": {"f_ch_xc": 0.50, "f_pr_xc": 0.15, "f_li_xc": 0.02, "f_xI_xc": 0.30, "f_sI_xc": 0.03}
            },
            "koyun": {
                "name": "Koyun Gübresi",
                "desc": "Sığır gübresine benzer ancak daha yoğun kuru madde.",
                "kinetics": {"k_dis": 0.12, "k_hyd_ch": 0.22, "k_hyd_pr": 0.20, "k_hyd_li": 0.12},
                "stoich": {"f_ch_xc": 0.35, "f_pr_xc": 0.25, "f_li_xc": 0.08, "f_xI_xc": 0.20, "f_sI_xc": 0.12}
            },
            "tavsan": {
                "name": "Tavşan Gübresi",
                "desc": "Azotça zengin, orta dereceli lif içeriği.",
                "kinetics": {"k_dis": 0.18, "k_hyd_ch": 0.30, "k_hyd_pr": 0.35, "k_hyd_li": 0.15},
                "stoich": {"f_ch_xc": 0.38, "f_pr_xc": 0.28, "f_li_xc": 0.04, "f_xI_xc": 0.20, "f_sI_xc": 0.10}
            }
        }

    def list_manures(self):
        print("\n" + "="*60)
        print("=== MEVCUT GÜBRE TÜRLERİ ===")
        print("="*60)
        print(f"{'Anahtar':<10} | {'Gübre Adı':<20} | {'Açıklama'}")
        print("-" * 60)
        for key, val in self.manure_data.items():
            print(f"{key:<10} | {val['name']:<20} | {val['desc']}")
        print("="*60)

    def create_hybrid_manure(self, mixture_dict):
        """Birden fazla gübreyi karıştırıp hibrit profili oluşturur."""
        hybrid_kinetics = {"k_dis": 0.0, "k_hyd_ch": 0.0, "k_hyd_pr": 0.0, "k_hyd_li": 0.0}
        hybrid_stoich = {"f_ch_xc": 0.0, "f_pr_xc": 0.0, "f_li_xc": 0.0, "f_xI_xc": 0.0, "f_sI_xc": 0.0}
        
        total_weight = sum(mixture_dict.values())
        if total_weight == 0:
            print("\n[HATA] Toplam karışım oranı 0 olamaz!")
            return None
            
        for key, weight in mixture_dict.items():
            if key not in self.manure_data:
                print(f"\n[HATA] '{key}' isimli gübre bulunamadı! Lütfen listedeki anahtarları kontrol edin.")
                return None
                
            data = self.manure_data[key]
            normalized_weight = weight / total_weight
            
            for k_key in hybrid_kinetics:
                hybrid_kinetics[k_key] += data['kinetics'][k_key] * normalized_weight
                
            for s_key in hybrid_stoich:
                hybrid_stoich[s_key] += data['stoich'][s_key] * normalized_weight
                
        hybrid_data = {
            "name": f"Hibrit Karışım ({', '.join([f'{k}: %{int((v/total_weight)*100)}' for k,v in mixture_dict.items()])})",
            "desc": "Kullanıcı tarafından oluşturulan özel karışım.",
            "kinetics": hybrid_kinetics,
            "stoich": hybrid_stoich
        }
        return hybrid_data

    def select_manure(self):
        while True:
            print("\n" + "="*60)
            print("=== PYADM1 - SİMÜLASYON TÜRÜ SEÇİMİ ===")
            print("="*60)
            print("1. Tek bir gübre türü simüle et")
            print("2. Hibrit (Karışım) gübre simüle et")
            print("Çıkış için 'q' yazın")
            
            sim_type = input("\nSeçiminiz (1/2/q): ").lower().strip()
            
            if sim_type == 'q':
                print("Simülasyon iptal edildi. Program kapatılıyor...")
                sys.exit()
                
            elif sim_type == '1':
                self.list_manures()
                choice = input("\nLütfen simüle etmek istediğiniz gübre anahtarını girin: ").lower().strip()
                data = self.manure_data.get(choice)
                if data:
                    print(f"\n[BAŞARILI] {data['name']} parametreleri PyADM1'e aktarılıyor...")
                    return data
                else:
                    print("\n[HATA] Geçersiz seçim.")
                    
            elif sim_type == '2':
                self.list_manures()
                print("\nHibrit karışımı girmek için gübre anahtarlarını ve oranlarını virgülle ayırarak yazın.")
                print("Örnek giriş: sigir:70, tavuk:30")
                mix_input = input("Karışım oranları: ").lower().strip()
                
                try:
                    # Kullanıcının girdiği metni temizleyip sözlüğe çeviriyoruz
                    mixture_dict = {}
                    parts = mix_input.split(',')
                    for part in parts:
                        key, ratio = part.split(':')
                        mixture_dict[key.strip()] = float(ratio.strip())
                        
                    hybrid_data = self.create_hybrid_manure(mixture_dict)
                    if hybrid_data:
                        print(f"\n[BAŞARILI] {hybrid_data['name']} oluşturuldu ve aktarılıyor...")
                        return hybrid_data
                except Exception as e:
                    print("\n[HATA] Hatalı giriş formatı! Lütfen aralarda virgül ve iki nokta kullanarak (örn: sigir:70, at:30) girin.")
            else:
                print("\n[HATA] Geçersiz bir tuşa bastınız. Lütfen 1 veya 2'yi seçin.")