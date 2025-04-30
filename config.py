# --------------------------------------
# 1. CATEGORIAS PARA CLASSIFICAÇÃO
# --------------------------------------

CATEGORIAS = {
    "MANUTENCAO": {
    "VIAGEM": ["MANUTENCAO", "BORRACHARIA", "LAVAGEM"],
    "FIXA": ["MANUTENCAO", "BORRACHARIA", "PLANO MANUTENCAO", "PNEU", "LAVAGEM", "MECANICO"]
    },
    
    "FINANCEIRO": {  
    "RECEITA": ["FRETE_IDA", "FRETE_VOLTA", "FRETE_EXTRA"],  
    "DESPESA": ["COMBUSTIVEL", "PEDAGIO", "ALIMENTACAO"],  
    "IMPOSTOS": ["IMPOSTO", "DETRAN"],  
    "CAPEX": ["PRESTACAO"]  
    },  
    
    "OPERACAO": {  
        "EFICIENCIA": ["KM_TOTAL", "TEMPO_VIAGEM"],  
        "OCORRENCIAS": ["AVARIA", "MULTAS"]  
    },  
}

# --------------------------------------
# 2. CONFIGURAÇÕES DE VISUALIZAÇÃO
# --------------------------------------

VIZ = {
    "CORES": {
    "POSITIVO": "#4CAF50", # verde
    "NEGATIVO": "#F44336", # vermelho
    "NEUTRO": "#2196F3" # azul
    },
    "FORMATOS": {
    "DATA": "%d/%m/%Y",
    "MOEDA": "R$ %.2f"
    }
}

# --------------------------------------
# 3. TEXTO E MENSAGENS
# --------------------------------------

TEXTO = {
    "FILTROS": {
    "TITULO": "🔍 Filtros Integrados",
    "VEICULOS": "Selecione os veículos:",
    "MOTORISTAS": "Selecione os motoristas:"
    },
    "ERROS": {
    "DIVISAO_ZERO": "N/A (divisão por zero)",
    "DADOS_VAZIOS": "Dados insuficientes para cálculo"
    }
}
