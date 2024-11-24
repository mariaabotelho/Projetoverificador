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

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    date: Optional[str] = None
    excerpt: Optional[str] = None

class FakeNewsChecker:
    def __init__(self):
        self.groq_api_key = "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"
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=self.groq_api_key,
            model_name="llama3-8b-8192"
        )

        self.verification_prompt = PromptTemplate(
            input_variables=["query", "search_results", "article_excerpts", "article_urls", "confirming_excerpts", "contradicting_excerpts"],
            template="""Analise a seguinte afirmação e determine se ela é verdadeira ou falsa baseado nas evidências encontradas:

Afirmação a ser verificada: {query}

Resultados da pesquisa encontrados:
{search_results}

Trechos relevantes dos artigos:
{article_excerpts}

URLs das fontes consultadas:
{article_urls}

Trechos que confirmam a afirmação:
{confirming_excerpts}

Trechos que contradizem a afirmação:
{contradicting_excerpts}

Por favor, forneça:
1. Um resumo das principais evidências encontradas
2. Análise da credibilidade das fontes
3. Verificação de contradições ou inconsistências
4. Sua conclusão final sobre a veracidade da afirmação
5. Nível de confiança na análise (alto/médio/baixo)
6. As URLs e as datas de todas as fontes consultadas"""
        )

        self.verification_chain = LLMChain(
            llm=self.llm,
            prompt=self.verification_prompt
        )

    def extract_excerpt(self, content: str) -> str:
        """Extrai um trecho relevante do conteúdo"""
        if not content:
            return ""
        sentences = content.split('.')
        return '. '.join(sentences[:3]) + '.'

    def search_duckduckgo(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Realiza busca no DuckDuckGo e extrai os resultados"""
        url = f"https://duckduckgo.com/html/?q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        results = []
        for article in soup.find_all('article', {'data-nrn': 'result'})[:max_results]:
            try:
                title_elem = article.find('a', {'data-testid': 'result-title-a'})
                title = title_elem.get_text(strip=True) if title_elem else ''
                url = title_elem.get('href') if title_elem else ''
                snippet_elem = article.find('div', {'data-result': 'snippet'})
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                source_elem = article.find('p', class_='fOCEb2mA3YZTJXXjpgdS')
                source = source_elem.get_text(strip=True) if source_elem else ''
                date_elem = article.find('span', class_='MILR5XIVy9h75WrLvKiq')
                date = date_elem.get_text(strip=True) if date_elem else None

                if title and url:
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source=source,
                        date=date
                    ))
            except Exception as e:
                st.error(f"Erro ao processar resultado: {e}")
                continue

        return results

    def extract_article_content(self, url: str) -> Optional[Tuple[str, str, str]]:
        """Extrai o conteúdo do artigo usando múltiplos métodos"""
        try:
            downloaded = trafilatura.fetch_url(url)
            content = trafilatura.extract(downloaded, include_comments=False)

            if content:
                confirming_excerpt, contradicting_excerpt = self.extract_relevant_excerpts(content)
                return content, confirming_excerpt, contradicting_excerpt

            loader = WebBaseLoader(url)
            docs = loader.load()
            content = "\n".join(doc.page_content for doc in docs)

            if content:
                confirming_excerpt, contradicting_excerpt = self.extract_relevant_excerpts(content)
                return content, confirming_excerpt, contradicting_excerpt

            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                elem.decompose()

            content = soup.get_text(separator='\n', strip=True)
            confirming_excerpt, contradicting_excerpt = self.extract_relevant_excerpts(content)
            return content, confirming_excerpt, contradicting_excerpt

        except Exception as e:
            st.error(f"Erro ao extrair conteúdo de {url}: {e}")
            return None, None, None

    def extract_relevant_excerpts(self, content: str) -> Tuple[str, str]:
        """Extrai trechos relevantes que confirmam ou contradizem a afirmação"""
        confirming_excerpt = ""
        contradicting_excerpt = ""

        if content:
            lines = content.split("\n")
            for line in lines:
                if "confirma" in line.lower():
                    confirming_excerpt += line + "\n"
                elif "contradiz" in line.lower():
                    contradicting_excerpt += line + "\n"

        return confirming_excerpt.strip(), contradicting_excerpt.strip()

    def verify_claim(self, query: str) -> Tuple[str, List[SearchResult]]:
        """Verifica uma afirmação usando busca e análise"""
        with st.status("Pesquisando fontes..."):
            search_results = self.search_duckduckgo(query)

        with st.status("Extraindo e analisando conteúdo..."):
            articles_content = []
            article_excerpts = []
            article_urls = []
            confirming_excerpts = []
            contradicting_excerpts = []

            for result in search_results:
                content, confirming_excerpt, contradicting_excerpt = self.extract_article_content(result.url)
                if content:
                    articles_content.append(f"Fonte: {result.source}\nTítulo: {result.title}\nConteúdo: {content}\n")
                    article_excerpts.append(f"De {result.source}: '{self.extract_excerpt(content)}'")
                    article_urls.append(result.url)
                    if confirming_excerpt:
                        confirming_excerpts.append(f"De {result.source}: '{confirming_excerpt}'")
                    if contradicting_excerpt:
                        contradicting_excerpts.append(f"De {result.source}: '{contradicting_excerpt}'")
                result.excerpt = self.extract_excerpt(content) if content else ""

            search_summary = "\n".join([
                f"Título: {r.title}\nFonte: {r.source}\nData: {r.date}\nResumo: {r.snippet}\n"
                for r in search_results
            ])

        with st.status("Gerando análise final..."):
            analysis = self.verification_chain.run(
                query=query,
                search_results=search_summary,
                article_excerpts="\n".join(article_excerpts),
                article_urls="\n".join(article_urls),
                confirming_excerpts="\n".join(confirming_excerpts),
                contradicting_excerpts="\n".join(contradicting_excerpts)
            )

        return analysis, search_results

def main():
    st.set_page_config(
        page_title="Verificador de Notícias",
        page_icon="🔍",
        layout="wide"
    )

    st.title("📰 Verificador de Notícias")
    st.write("Digite uma afirmação para verificar sua veracidade com base em múltiplas fontes.")

    checker = FakeNewsChecker()
    
    query = st.text_area(
        "Digite a afirmação que deseja verificar:",
        height=100,
        placeholder="Ex: cloroquina ajuda no tratamento de COVID"
    )
    
    if st.button("Verificar", type="primary"):
        if query:
            try:
                analysis, results = checker.verify_claim(query)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Análise Detalhada")
                    st.markdown(analysis)
                
                with col2:
                    st.subheader("Fontes Consultadas")
                    for idx, result in enumerate(results, 1):
                        with st.expander(f"{idx}. {result.title}"):
                            st.write(f"**Fonte:** {result.source}")
                            st.write(f"**Data:** {result.date}")
                            st.write(f"**URL:** {result.url}")
                            if result.excerpt:
                                st.write(f"**Trecho:** {result.excerpt}")
                
            except Exception as e:
                st.error(f"Ocorreu um erro durante a análise: {str(e)}")
        else:
            st.warning("Por favor, digite uma afirmação para verificar.")

if __name__ == "__main__":
    main()
