from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import requests, os

load_dotenv()

def get_video_transcript(video_id: str) -> str:
    """Extract transcript from YouTube video with proxy support"""
    try:
        api = YouTubeTranscriptApi()
        
        proxy_key = os.getenv("YOUTUBE_PROXY_KEY")

        # Use a free proxy
        proxies = {
            'http': 'http://proxy.scrapeops.io:5353?api_key=YOUR_API_KEY',
            'https': 'http://proxy.scrapeops.io:5353?api_key=YOUR_API_KEY',
        }
        
        transcript_list = api.list(video_id=video_id).find_transcript(['en']).fetch()
        transcript = " ".join(chunk.text for chunk in transcript_list)
        return transcript
    
    except TranscriptsDisabled:
        raise Exception(f"❌ Transcripts are disabled for this video")
    except Exception as e:
        raise Exception(f"❌ Error: {str(e)}")
    

def get_transcript(video_id: str) -> str:
    """Fetch transcript from YouTube video"""
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id=video_id).find_transcript(['en']).fetch()
        transcript = " ".join(chunk.text for chunk in transcript_list)
        return transcript
    except TranscriptsDisabled:
        raise Exception(f"Transcripts are disabled for video: {video_id}")
    except Exception as e:
        raise Exception(f"Error fetching transcript: {str(e)}")


def create_chain(transcript: str):
    """Create RAG chain from transcript"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.create_documents([transcript])
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    prompt = PromptTemplate(
        template="""You are a helpful assistant. Answer ONLY from the provided transcript context. 
    If the context is insufficient, just say you don't know.

    Context:
    {context}

    Question: {question}
    """,
            input_variables=["context", "question"]
    )
    
    def format_docs(retrieved_docs):
        return "\n\n".join(doc.page_content for doc in retrieved_docs)
    
    parallel_chain = RunnableParallel({
        "context": retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough()
    })
    
    parser = StrOutputParser()
    final_chain = parallel_chain | prompt | llm | parser
    
    return final_chain


def get_answer(chain, question: str) -> str:
    """Get answer from chain"""
    return chain.invoke(question)