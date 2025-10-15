"""
Supabase client for database operations
"""
import os
from typing import Dict, List, Optional, Any
from supabase import create_client, Client


class SupabaseClient:
    """Client for interacting with Supabase database"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ):
        """
        Initialize Supabase client
        
        Args:
            url: Supabase URL (defaults to SUPABASE_URL env var)
            key: Supabase service role key (defaults to SUPABASE_SERVICE_ROLE_KEY env var)
        """
        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.client: Client = create_client(url, key)
    
    def save_signals(self, signals: List[Dict[str, Any]]) -> None:
        """
        Save signal data to database
        
        Args:
            signals: List of signal dictionaries to insert
        """
        self.client.table("signals").insert(signals).execute()
    
    def get_signals(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve signals from database
        
        Args:
            ticker: Filter by ticker symbol
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of signal records
        """
        query = self.client.table("signals").select("*")
        
        if ticker:
            query = query.eq("ticker", ticker)
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
        
        response = query.execute()
        return response.data
    
    def save_scores(self, scores: List[Dict[str, Any]]) -> None:
        """
        Save directional scores to database
        
        Args:
            scores: List of score dictionaries to insert
        """
        self.client.table("scores").insert(scores).execute()
    
    def get_scores(
        self,
        ticker: Optional[str] = None,
        min_abs_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve directional scores from database
        
        Args:
            ticker: Filter by ticker symbol
            min_abs_score: Minimum absolute score threshold
            
        Returns:
            List of score records
        """
        query = self.client.table("scores").select("*")
        
        if ticker:
            query = query.eq("ticker", ticker)
        
        response = query.execute()
        data = response.data
        
        if min_abs_score is not None:
            data = [
                d for d in data 
                if abs(d.get("dir_score", 0)) >= min_abs_score
            ]
        
        return data

