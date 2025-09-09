"""
Pagination Service

This service handles pagination based on user settings including:
- Results per page configuration
- Page calculation
- Pagination metadata
"""

from typing import Dict, Any, Optional
from flask_login import current_user
from sqlalchemy.orm import Query

from src.database.models import UserSettings
from utils.logger import logger

class PaginationService:
    """Service for handling pagination based on user settings."""

    def __init__(self):
        self.default_per_page = 10
        self.min_per_page = 5
        self.max_per_page = 100

    def get_user_per_page(self) -> int:
        """Get current user's results per page setting."""
        try:
            if current_user and current_user.is_authenticated:
                user_settings = UserSettings.get_or_create_for_user(current_user.id)
                per_page = user_settings.results_per_page or self.default_per_page

                # Validate range
                if per_page < self.min_per_page:
                    per_page = self.min_per_page
                elif per_page > self.max_per_page:
                    per_page = self.max_per_page

                return per_page
            else:
                return self.default_per_page
        except Exception as e:
            logger.warning(f"Failed to get user pagination setting: {e}")
            return self.default_per_page

    def paginate_query(self, query: Query, page: int = 1, per_page: Optional[int] = None) -> Dict[str, Any]:
        """
        Paginate a SQLAlchemy query based on user settings.

        Args:
            query: SQLAlchemy query to paginate
            page: Current page number (1-based)
            per_page: Items per page (uses user setting if None)

        Returns:
            Dictionary with pagination data
        """
        if per_page is None:
            per_page = self.get_user_per_page()

        # Ensure page is at least 1
        page = max(1, page)

        # Get total count
        total = query.count()

        # Calculate pagination
        total_pages = (total + per_page - 1) // per_page  # Ceiling division
        has_prev = page > 1
        has_next = page < total_pages

        # Get items for current page
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None,
            'start_index': offset + 1 if items else 0,
            'end_index': min(offset + per_page, total)
        }

    def get_pagination_info(self, pagination_data: Dict[str, Any]) -> str:
        """Get human-readable pagination info."""
        if pagination_data['total'] == 0:
            return "No results found"

        start = pagination_data['start_index']
        end = pagination_data['end_index']
        total = pagination_data['total']

        if start == end:
            return f"Showing result {start} of {total}"
        else:
            return f"Showing results {start}-{end} of {total}"

# Global instance
pagination_service = PaginationService()