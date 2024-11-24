import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import os
import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.document_loaders import WebBaseLoader
import trafilatura

# [Classes SearchResult e FakeNewsChecker permanecem as mesmas]

def create_sidebar():
    with st.sidebar:
        st.image("logo verifik.png", width=100)
        st.title("Sobre o Verifik")
        
        st.write("""
        O Verifik é uma ferramenta de verificação de notícias que surge da 
        necessidade de combater a desinformação em uma era de sobrecarga 
        informacional nas redes sociais.
        """)
        
        st.subheader("Objetivo")
        st.write("""
        Oferecer uma ferramenta que automatiza o processo de verificação,
        consultando múltiplas fontes e analisando a credibilidade das 
        informações de forma rápida e acessível.
        """)
        
        st.subheader("Criadoras")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("Maria Botelho")
        with col2:
            st.caption("Clarissa Treptow")
        with col3:
            st.caption("Catarina Moll")

def show_usage_tips():
    with st.expander("📝 Dicas para obter melhores resultados"):
        st.info("""
        **Para uma verificação mais precisa:**
        
        1. **Ortografia correta**: Verifique a grafia dos nomes e palavras
        2. **Seja específico**: Quanto mais detalhes, melhor será a análise
        3. **Inclua datas**: Quando possível, especifique o período do evento
        
        **Exemplo de uma boa consulta:**
        "Ministério da Saúde confirmou 5 casos de dengue tipo 3 em São Paulo em janeiro de 2024"
        """)
        
        st.warning("""
        **Limitações importantes:**
        - Base de dados limitada até 2022
        - Resultados podem variar dependendo das fontes disponíveis
        """)
        
        st.error("""
        **Disclaimer**: O Verifik utiliza inteligência artificial para análise.
        Embora busquemos a máxima precisão, recomendamos sempre verificar as
        fontes originais para informações críticas.
        """)

def main():
    st.set_page_config(
        page_title="Verifik",
        page_icon="🔍",
        layout="wide"
    )

    create_sidebar()

    # Cabeçalho principal
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("logo verifik.png", width=200)
    with col_title:
        st.title("Verifik")
        st.subheader("Verificação inteligente de notícias")

    # Dicas de uso
    show_usage_tips()

    # Container principal
    with st.container():
        st.write("---")
        query = st.text_area(
            "Digite a afirmação que deseja verificar:",
            height=100,
            placeholder="Ex: Ministério da Saúde confirmou 5 casos de dengue tipo 3 em São Paulo em janeiro de 2024"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            verify_button = st.button("Verificar", type="primary", use_container_width=True)

    if verify_button and query:
        checker = FakeNewsChecker()
        
        try:
            with st.spinner("Analisando..."):
                analysis, results = checker.verify_claim(query)
            
            # Resultados em tabs
            tab1, tab2 = st.tabs(["📊 Análise", "🔎 Fontes"])
            
            with tab1:
                st.markdown(analysis)
            
            with tab2:
                for idx, result in enumerate(results, 1):
                    with st.expander(f"Fonte {idx}: {result.title}"):
                        cols = st.columns([2, 1])
                        with cols[0]:
                            st.write(f"**Fonte:** {result.source}")
                            st.write(f"**Data:** {result.date}")
                        with cols[1]:
                            st.write(f"**URL:** {result.url}")
                        if result.excerpt:
                            st.info(f"**Trecho relevante:** {result.excerpt}")

        except Exception as e:
            st.error(f"Ocorreu um erro durante a análise: {str(e)}")
            
    elif verify_button:
        st.warning("Por favor, digite uma afirmação para verificar.")

if __name__ == "__main__":
    main()
