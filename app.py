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

# Reutilizando sua classe SearchResult
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    date: Optional[str] = None
    excerpt: Optional[str] = None

# Reutilizando sua classe FakeNewsChecker com pequenas adaptações
class FakeNewsChecker:
    def __init__(self):
        # Usando st.secrets para a chave API no Streamlit
        self.groq_api_key = st.secrets["GROQ_API_KEY"]
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=self.groq_api_key,
            model_name="llama3-8b-8192"
        )

        # O resto da sua classe FakeNewsChecker permanece igual
        # [Cole aqui o resto do código da sua classe FakeNewsChecker]

def main():
    st.title("Verificador de Notícias")
    st.write("Digite uma afirmação para verificar sua veracidade")
    
    # Criando o checker
    checker = FakeNewsChecker()
    
    # Campo de entrada para a afirmação
    claim = st.text_area("Digite a afirmação que deseja verificar:", height=100)
    
    # Botão para iniciar a verificação
    if st.button("Verificar"):
        if claim:
            # Mostrar um spinner durante a análise
            with st.spinner("Analisando a afirmação..."):
                try:
                    analysis, results = checker.verify_claim(claim)
                    
                    # Exibindo as fontes consultadas
                    st.subheader("Fontes Consultadas")
                    for idx, result in enumerate(results, 1):
                        with st.expander(f"Fonte {idx}: {result.title}"):
                            st.write(f"**Fonte:** {result.source}")
                            st.write(f"**Data:** {result.date}")
                            st.write(f"**URL:** {result.url}")
                            st.write(f"**Resumo:** {result.snippet}")
                    
                    # Exibindo a análise
                    st.subheader("Análise")
                    st.write(analysis)
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro durante a análise: {str(e)}")
        else:
            st.warning("Por favor, digite uma afirmação para verificar.")

if __name__ == "__main__":
    main()
