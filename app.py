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


def create_sidebar():
    with st.sidebar:
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
        st.caption("Maria Botelho")
        st.caption("Clarissa Treptow")
        st.caption("Catarina Moll")

def show_usage_tips():
    with st.expander("📝 Dicas para obter melhores resultados"):
        st.info("""
        **Para uma verificação mais precisa:**
        
        1. **Ortografia correta**: Verifique a grafia dos nomes e palavras
        2. **Seja específico**: Quanto mais detalhes, melhor será a análise
        3. **Inclua datas**: Quando possível, especifique o período do evento
        
        **Exemplo de uma boa consulta:**
        "Michael Phelps ganhou 8 medalhas de ouro nas Olimpíadas de Pequim em 2008"
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
    # Removendo o título redundante
        st.subheader("Verificação inteligente de notícias")

    # Dicas de uso
    show_usage_tips()

    # Container principal
    with st.container():
        st.write("---")
        query = st.text_area(
            "Digite a afirmação que deseja verificar:",
            height=100,
            placeholder="Ex: Brasil ganhou a Copa América de 2019 vencendo o Peru na final"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            verify_button = st.button("Verificar", type="primary", use_container_width=True)

        if verify_button and query:
            checker = FakeNewsChecker()
            
            try:
                with st.spinner("Analisando..."):
                    analysis, results = checker.verify_claim(query)
                
                # Função de classificação
                def classify_result(analysis_lower):
                    # Indicadores fortes de FALSO
                    false_indicators = [
                        "falsa",
                        "não é verdadeira",
                        "não há evidências que suportem",
                        "é incorreta",
                        "não corresponde aos fatos"
                    ]
                    
                    # Indicadores fortes de VERDADEIRO
                    true_indicators = [
                        "verdadeira",
                        "é correta",
                        "é confirmada",
                        "evidências confirmam",
                        "fontes confirmam"
                    ]
                    
                    # Indicadores de INCONCLUSIVO
                    inconclusive_indicators = [
                        "não há consenso",
                        "evidências são inconclusivas",
                        "algumas fontes sugerem",
                        "embora",
                        "entretanto",
                        "por outro lado",
                        "mais estudos são necessários",
                        "evidência é limitada",
                        "não é possível concluir",
                        "é amplamente contestada",
                        "há discordância",
                        "nem todas as fontes concordam"
                    ]
                    
                    # Verificar se há indicadores de resultados mistos
                    has_mixed_evidence = any(indicator in analysis_lower for indicator in inconclusive_indicators)
                    
                    # Verificar se há termos que frequentemente aparecem juntos em evidências conflitantes
                    has_conflicting_terms = (
                        ("algumas" in analysis_lower and "outras" in analysis_lower) or
                        ("confirma" in analysis_lower and "contradiz" in analysis_lower) or
                        ("evidências" in analysis_lower and "contraditórias" in analysis_lower)
                    )
                    
                    # Lógica de classificação
                    if has_mixed_evidence or has_conflicting_terms:
                        st.info("ℹ️ INCONCLUSIVO", icon=None)
                    elif any(indicator in analysis_lower for indicator in false_indicators):
                        st.error("❌ FALSO", icon=None)
                    elif any(indicator in analysis_lower for indicator in true_indicators):
                        st.success("✅ VERDADEIRO", icon=None)
                    else:
                        st.info("ℹ️ INCONCLUSIVO", icon=None)  # Caso padrão se nenhum padrão claro for encontrado

                # Usar a nova função de classificação
                analysis_lower = analysis.lower()
                classify_result(analysis_lower)
                
                # Análise detalhada em container
                with st.container():
                    st.markdown(analysis)
                    
                # Fontes em expanders
                for idx, result in enumerate(results, 1):
                    with st.expander(f"Fonte {idx}: {result.title}"):
                        st.write(f"**Fonte:** {result.source}")
                        st.write(f"**Data:** {result.date}")
                        st.write(f"**URL:** {result.url}")
                        if result.excerpt:
                            st.info(f"**Trecho relevante:** {result.excerpt}")

            except Exception as e:
                st.error(f"Ocorreu um erro durante a análise: {str(e)}")

        elif verify_button:
            st.warning("Por favor, digite uma afirmação para verificar.")


if __name__ == "__main__":
    main()
