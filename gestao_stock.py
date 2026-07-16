import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="GAIP - Gestao de Stock",
    page_icon="key",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 20px !important;
        font-weight: bold;
        border-radius: 10px;
    }
    .low-stock {
        background-color: #ffcccc;
        color: #990000;
        padding: 5px;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "stock_gaip.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT NOT NULL,
            referencia TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            posicao TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 10
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_mov TEXT NOT NULL,
            produto_id INTEGER,
            quantidade INTEGER,
            ref_interna TEXT,
            cliente TEXT,
            colaborador TEXT,
            data TEXT,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    """)
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        dados_iniciais = [
            ('JMA', 'D002', 'Chave de Pontos', 'Painel A - Gaveta 1', 120, 100),
            ('Silca', 'D004', 'Chave de Pontos', 'Painel A - Gaveta 2', 80, 100),
            ('JMA', 'YA-85', 'Chave Plana', 'Painel B - Gancho 5', 15, 10),
            ('CISA', 'C10', 'Chave de Palhetão', 'Painel C - Gaveta 4', 8, 10),
        ]
        c.executemany("""
            INSERT INTO produtos (marca, referencia, tipo, posicao, stock, stock_minimo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, dados_iniciais)
        conn.commit()
    conn.close()

init_db()

def obter_produtos():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM produtos", conn)
    conn.close()
    return df

def registar_baixa(produto_id, qtd, ref_interna, cliente, colaborador):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE produtos SET stock = stock - ? WHERE id = ?", (qtd, produto_id))
    c.execute("""
        INSERT INTO movimentacoes (tipo_mov, produto_id, quantidade, ref_interna, cliente, colaborador, data)
        VALUES ('BAIXA', ?, ?, ?, ?, ?, ?)
    """, (produto_id, qtd, ref_interna, cliente, colaborador, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def registar_entrada(marca, ref, tipo, posicao, qtd, min_stock):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, stock FROM produtos WHERE referencia = ?", (ref,))
    res = c.fetchone()
    if res:
        prod_id, stock_atual = res
        novo_stock = stock_atual + qtd
        c.execute("UPDATE produtos SET stock = ?, posicao = ?, stock_minimo = ? WHERE id = ?", (novo_stock, posicao, min_stock, prod_id))
        prod_id_mov = prod_id
    else:
        c.execute("""
            INSERT INTO produtos (marca, referencia, tipo, posicao, stock, stock_minimo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (marca, ref, tipo, posicao, qtd, min_stock))
        prod_id_mov = c.lastrowid
        
    c.execute("""
        INSERT INTO movimentacoes (tipo_mov, produto_id, quantidade, data)
        VALUES ('ENTRADA', ?, ?, ?)
    """, (prod_id_mov, qtd, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

st.title("GAIP - Controlo de Stock")
st.subheader("Sistema Inteligente Multiplataforma")

menu = st.radio("Escolha a Operacao:", ["Dar Baixa (Consumo)", "Registar Entrada / Novo Perfil", "Ver Inventario / Alertas"], horizontal=True)

df_produtos = obter_produtos()

if menu == "Dar Baixa (Consumo)":
    st.markdown("### Registar Consumo no Posto de Trabalho")
    df_produtos['display'] = df_produtos['referencia'] + " (" + df_produtos['marca'] + " - " + df_produtos['tipo'] + ") - Local: " + df_produtos['posicao']
    opcoes_produtos = df_produtos.set_index('id')['display'].to_dict()
    
    prod_selecionado = st.selectbox("Selecione o Perfil da Chave:", options=list(opcoes_produtos.keys()), format_func=lambda x: opcoes_produtos[x])
    
    col1, col2 = st.columns(2)
    with col1:
        qtd = st.number_input("Quantidade Consumida:", min_value=1, value=1, step=1)
    with col2:
        colaborador = st.selectbox("Colaborador:", ["Nuno", "Marco", "Marcela", "Outro"])
        
    ref_interna = st.text_input("Referencia Interna / Servico (Ex: Copia casa do Nuno):", placeholder="Opcional")
    cliente = st.text_input("Cliente / Obra:", placeholder="Opcional")
    
    if st.button("CONFIRMAR SAIDA DE STOCK", type="primary"):
        stock_atual = df_produtos[df_produtos['id'] == prod_selecionado]['stock'].values[0]
        ref_nome = df_produtos[df_produtos['id'] == prod_selecionado]['referencia'].values[0]
        
        if stock_atual < qtd:
            st.error(f"Erro: Stock insuficiente! Apenas existem {stock_atual} unidades deste perfil em stock.")
        else:
            registar_baixa(prod_selecionado, qtd, ref_interna, cliente, colaborador)
            st.success(f"Sucesso! {qtd} unidade(s) da chave {ref_nome} retiradas com sucesso!")
            st.rerun()

elif menu == "Registar Entrada / Novo Perfil":
    st.markdown("### Entrada de Stock / Cadastro de Perfis")
    marca = st.text_input("Marca do Perfil (Ex: JMA, Silca):")
    referencia = st.text_input("Referencia Original (Ex: D002, YA-85):")
    tipo = st.selectbox("Tipo de Chave:", ["Chave Plana", "Chave de Pontos", "Chave de Palhetao", "Cilindro", "Fechadura", "Cadeado/Outros"])
    posicao = st.text_input("Posicao Fisica (Onde a chave fica guardada/exposta):")
    
    col1, col2 = st.columns(2)
    with col1:
        quantidade = st.number_input("Quantidade a Adicionar:", min_value=1, value=10, step=1)
    with col2:
        min_stock = st.number_input("Stock Minimo Recomendado:", min_value=1, value=10, step=1)
        
    if st.button("REGISTAR ENTRADA"):
        if marca and referencia and posicao:
            registar_entrada(marca, referencia, tipo, posicao, quantidade, min_stock)
            st.success(f"Entrada de {quantidade} unidades da referencia {referencia} registada!")
            st.rerun()
        else:
            st.warning("Por favor, preencha todos os campos obrigatorios (Marca, Referencia e Posicao).")

elif menu == "Ver Inventario / Alertas":
    st.markdown("### Estado Atual do Stock")
    alertas = df_produtos[df_produtos['stock'] < df_produtos['stock_minimo']]
    if not alertas.empty:
        st.error(f"ATENCAO: Existem {len(alertas)} perfis abaixo do stock minimo recomendado!")
        st.dataframe(alertas[['marca', 'referencia', 'tipo', 'posicao', 'stock', 'stock_minimo']].rename(columns={
            'marca': 'Marca', 'referencia': 'Referência', 'tipo': 'Tipo', 'posicao': 'Posição', 'stock': 'Stock Atual', 'stock_minimo': 'Mínimo'
        }), use_container_width=True)
    else:
        st.success("Todos os perfis possuem stock saudavel acima do minimo recomendado!")
        
    st.markdown("#### Inventario Completo")
    st.dataframe(df_produtos[['marca', 'referencia', 'tipo', 'posicao', 'stock', 'stock_minimo']].rename(columns={
        'marca': 'Marca', 'referencia': 'Referência', 'tipo': 'Tipo', 'posicao': 'Posição', 'stock': 'Stock Atual', 'stock_minimo': 'Mínimo'
    }), use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Acoes Administrativas")
    if st.button("Simular Envio de Relatorio para contabilidade@gaip.pt"):
        st.info("A gerar PDF com as existencias do dia...")
        st.success("Relatorio mensal enviado com sucesso para: contabilidade@gaip.pt!")
