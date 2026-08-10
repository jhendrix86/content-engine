"""
Script to create a default tenant for existing data migration

This script creates a default tenant that can be used to assign
tenant_id to existing data during the migration process.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from loguru import logger
import uuid


async def create_default_tenant():
    """Create a default tenant for existing data migration."""
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if default tenant already exists
            result = await session.execute(
                select(Tenant).where(Tenant.slug == "default")
            )
            existing_tenant = result.scalar_one_or_none()
            
            if existing_tenant:
                logger.info(f"Default tenant already exists: {existing_tenant.id}")
                return existing_tenant.id
            
            # Create default tenant
            default_tenant = Tenant(
                id=uuid.uuid4(),
                name="Default Tenant",
                slug="default",
                description="Default tenant for migrating existing data",
                is_active=True
            )
            
            session.add(default_tenant)
            await session.commit()
            await session.refresh(default_tenant)
            
            logger.info(f"Created default tenant: {default_tenant.id}")
            logger.info(f"Use this tenant_id for migrating existing data: {default_tenant.id}")
            
            return default_tenant.id
            
        except Exception as e:
            logger.error(f"Failed to create default tenant: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    logger.info("Creating default tenant...")
    tenant_id = asyncio.run(create_default_tenant())
    logger.info(f"Default tenant ID: {tenant_id}")
