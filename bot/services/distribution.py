from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.lead import Lead, LeadDistribution
from bot.models.user import User
from bot.core.config import settings
import random

class DistributionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_eligible_users(self, lead: Lead, include_demo: bool = False) -> List[User]:
        """Get users eligible for receiving the lead based on category and city."""
        query = select(User).where(
            and_(
                User.is_active == True,
                or_(
                    and_(
                        User.categories.contains([lead.category]),
                        User.cities.contains([lead.city])
                    ),
                    User.is_demo == include_demo
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_groups(self, users: List[User], group_size: int = 3) -> List[List[User]]:
        """Split users into groups."""
        groups = []
        for i in range(0, len(users), group_size):
            groups.append(users[i:i + group_size])
        return groups

    async def get_next_group_index(self) -> int:
        """Get index of next group to receive leads."""
        # Get total number of leads
        total_leads = await self.session.scalar(select(func.count(Lead.id)))
        if total_leads is None:
            total_leads = 0
        return total_leads % 2

    async def create_distribution(self, lead: Lead, user: User, delay_hours: int = 0) -> LeadDistribution:
        """Create a lead distribution entry with optional delay."""
        distribution = LeadDistribution(
            lead_id=lead.id,
            user_id=user.id,
            sent_at=datetime.utcnow() + timedelta(hours=delay_hours)
        )
        self.session.add(distribution)
        await self.session.commit()
        return distribution

    async def distribute_lead(self, lead: Lead, include_demo: bool = False) -> List[LeadDistribution]:
        """Distribute lead to eligible users according to the specified algorithm."""
        # Get eligible users
        users = await self.get_eligible_users(lead, include_demo)
        if not users:
            return []

        # Split users into groups of 3
        user_groups = await self.get_user_groups(users, group_size=3)
        if not user_groups:
            return []

        # Determine which group should receive the lead
        group_index = await self.get_next_group_index()
        
        # If group_index is 1, we go in reverse order
        if group_index == 1:
            user_groups = list(reversed(user_groups))

        # Get the target group (first group after reordering)
        target_group = user_groups[0] if user_groups else []
        
        # Create distributions with delays
        distributions = []
        for i, user in enumerate(target_group):
            distribution = await self.create_distribution(
                lead=lead,
                user=user,
                delay_hours=i * settings.DISTRIBUTION_INTERVAL
            )
            distributions.append(distribution)
        
        return distributions

    async def create_demo_lead(self) -> Lead:
        """Create a demo lead for testing."""
        demo_data = {
            "name": random.choice(["Иван", "Петр", "Анна", "Мария"]),
            "phone": f"+7{random.randint(9000000000, 9999999999)}",
            "category": random.choice(settings.CATEGORIES),
            "city": random.choice(settings.CITIES),
            "description": "Демонстрационная заявка для тестирования",
            "area": random.randint(30, 150),
            "source_chat_id": 0,
            "source_message_id": 0
        }
        
        lead = Lead(**demo_data)
        self.session.add(lead)
        await self.session.commit()
        return lead

    async def get_pending_distributions(self) -> List[LeadDistribution]:
        """Get distributions that are ready to be sent."""
        query = select(LeadDistribution).where(
            and_(
                LeadDistribution.sent_at <= datetime.utcnow(),
                LeadDistribution.viewed_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def mark_distribution_viewed(self, distribution_id: int) -> Optional[LeadDistribution]:
        """Mark distribution as viewed."""
        query = select(LeadDistribution).where(LeadDistribution.id == distribution_id)
        result = await self.session.execute(query)
        distribution = result.scalar_one_or_none()
        
        if distribution:
            distribution.viewed_at = datetime.utcnow()
            await self.session.commit()
            
        return distribution 