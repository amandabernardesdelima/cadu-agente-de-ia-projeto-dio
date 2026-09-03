import pandas as pd

# ==============================
# 1. Carregar dados dos CSVs
# ==============================

def carregar_taxa_media(modalidade, csv_path="data/taxas_credito.csv"):
    """
    Retorna a taxa média mensal para uma modalidade específica.
    Se não encontrar, retorna a média geral.
    """
    df = pd.read_csv(csv_path)
    df_modalidade = df[df['MODALIDADE'].str.contains(modalidade, case=False)]
    if not df_modalidade.empty:
        return df_modalidade['TAXAS MÉDIAS (% a.m.)'].mean() / 100
    return df['TAXAS MÉDIAS (% a.m.)'].mean() / 100

def carregar_prazo_padrao(modalidade, csv_path="data/prazos_medios_por_modalidade.csv"):
    """
    Retorna o número médio de parcelas para uma modalidade.
    """
    df = pd.read_csv(csv_path)
    df_modalidade = df[df['modalidade'].str.contains(modalidade, case=False)]
    if not df_modalidade.empty:
        min_p = df_modalidade['prazo_min_parcelas'].values[0]
        max_p = df_modalidade['prazo_max_parcelas'].values[0]
        return int((min_p + max_p) / 2)
    return 12  # fallback

# ==============================
# 2. Fórmulas de cálculo
# ==============================

def calcular_price(principal, taxa, meses):
    """
    Sistema Price: parcelas fixas.
    """
    parcela = (principal * taxa) / (1 - (1 + taxa) ** -meses)
    total_pago = parcela * meses
    juros_total = total_pago - principal
    return {
        "parcela": round(parcela, 2),
        "total_pago": round(total_pago, 2),
        "juros_total": round(juros_total, 2)
    }

def calcular_sac(principal, taxa, meses):
    """
    Sistema SAC: amortização constante.
    """
    amortizacao = principal / meses
    saldo = principal
    parcelas = []
    juros_total = 0

    for m in range(1, meses+1):
        juros = saldo * taxa
        parcela = amortizacao + juros
        parcelas.append(round(parcela, 2))
        juros_total += juros
        saldo -= amortizacao

    total_pago = principal + juros_total
    return {
        "parcelas": parcelas,
        "total_pago": round(total_pago, 2),
        "juros_total": round(juros_total, 2),
        "amortizacao": round(amortizacao, 2)
    }

# ==============================
# 3. Função principal de simulação
# ==============================

def simular_credito(valor, modalidade="Crédito pessoal", taxa=None, meses=None, entrada=0, amortizacao=True):
    """
    Simula operação de crédito considerando entrada, taxa e prazo.
    - valor: valor total do bem/empréstimo
    - modalidade: tipo de crédito (ex.: 'veículos', 'imobiliário')
    - taxa: taxa de juros mensal (se None, busca média no CSV)
    - meses: número de parcelas (se None, busca média no CSV)
    - entrada: valor de entrada
    - amortizacao: True para calcular SAC e Price, False para apenas montante simples
    """
    principal = valor - entrada

    if taxa is None:
        taxa = carregar_taxa_media(modalidade)

    if meses is None:
        meses = carregar_prazo_padrao(modalidade)

    resultado = {
        "entrada": entrada,
        "valor_financiado": principal,
        "taxa": taxa,
        "meses": meses
    }

    if amortizacao:
        resultado["price"] = calcular_price(principal, taxa, meses)
        resultado["sac"] = calcular_sac(principal, taxa, meses)
    else:
        # Montante simples (juros compostos sem amortização detalhada)
        montante = principal * ((1 + taxa) ** meses)
        juros_total = montante - principal
        resultado["montante_final"] = round(montante, 2)
        resultado["juros_total"] = round(juros_total, 2)

    return resultado

# ==============================
# 4. Exemplo de uso
# ==============================

if __name__ == "__main__":
    # Usuário pede simulação de R$20.000 em financiamento de veículos, sem informar taxa
    resultado = simular_credito(valor=20000, modalidade="veículos", meses=36, entrada=5000, amortizacao=True)

    print("=== Simulação de Crédito ===")
    print(f"Valor total: R${20000}")
    print(f"Entrada: R${resultado['entrada']}")
    print(f"Valor financiado: R${resultado['valor_financiado']}")
    print(f"Taxa usada: {resultado['taxa']*100:.2f}% ao mês")
    print(f"Prazo: {resultado['meses']} meses\n")

    if "price" in resultado:
        print("Sistema Price:")
        print(f"Parcela fixa: R${resultado['price']['parcela']}")
        print(f"Total pago: R${resultado['price']['total_pago']}")
        print(f"Juros total: R${resultado['price']['juros_total']}\n")

    if "sac" in resultado:
        print("Sistema SAC:")
        print(f"Amortização constante: R${resultado['sac']['amortizacao']}")
        print(f"Primeira parcela: R${resultado['sac']['parcelas'][0]}")
        print(f"Última parcela: R${resultado['sac']['parcelas'][-1]}")
        print(f"Total pago: R${resultado['sac']['total_pago']}")
        print(f"Juros total: R${resultado['sac']['juros_total']}")
