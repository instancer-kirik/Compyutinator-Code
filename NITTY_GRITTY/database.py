import shutil
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import os
import logging
# Paths to the seed database and the user's local database
SEED_DB_PATH = 'seeds.db'
LOCAL_DB_PATH = 'computinator_data.db'

# Setup SQLAlchemy for both seed and local databases
seed_engine = create_engine(f'sqlite:///{SEED_DB_PATH}')
local_engine = create_engine(f'sqlite:///{LOCAL_DB_PATH}')
# Create a base class for SQLAlchemy models
Base = declarative_base()

# Define the UserAction model
class UserAction(Base):
    __tablename__ = 'user_actions'

    id = Column(Integer, primary_key=True)
    action_name = Column(String)
    action_type = Column(String)
    action_data = Column(String)
    pressed_count = Column(Integer)
    command = Column(String(512))

# Add new Risk model after UserAction model
class Risk(Base):
    __tablename__ = 'risks'

    id = Column(Integer, primary_key=True)
    description = Column(String)
    probability = Column(String)
    impact = Column(String)
    priority = Column(String)
    status = Column(String)
    mitigation = Column(String)
    reward_type = Column(String, nullable=True)
    estimated_value = Column(Integer, nullable=True)
    reward_probability = Column(String, nullable=True)
    date_created = Column(String)
    last_updated = Column(String)
    owner = Column(String, nullable=True)
    category_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)

# Create all tables in both seed and local databases (if they don't exist)
Base.metadata.create_all(seed_engine)  # Ensure seed DB has the correct schema
Base.metadata.create_all(local_engine)  # Ensure local DB has the correct schema

# Create a session factory for database interactions
SeedSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=seed_engine)
LocalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)

# Define the function to provide sessions for the seed database
def get_seed_db():
    """Yields a session for the seed database."""
    seed_db = SeedSessionLocal()
    try:
        yield seed_db
    finally:
        seed_db.close()

# Define the function to provide sessions for the local database
def get_local_db():
    """Yields a session for the local database."""
    local_db = LocalSessionLocal()
    try:
        yield local_db
    finally:
        local_db.close()

# Define the function to copy and merge data
def copy_and_merge_seed_data():
    """Copies and merges data from seeds.db to the local user database."""
    try:
        # Create sessions
        seed_db = SeedSessionLocal()
        local_db = LocalSessionLocal()

        # Copy UserAction data from seeds.db to local database
        seed_actions = seed_db.query(UserAction).all()
        
        for action in seed_actions:
            existing_action = local_db.query(UserAction).filter_by(action_name=action.action_name).first()
            if not existing_action:
                # If action does not exist in local DB, copy it over
                new_action = UserAction(
                    action_name=action.action_name,
                    action_type=action.action_type,
                    action_data=action.action_data,
                    pressed_count=action.pressed_count,
                    command=action.command
                )
                local_db.add(new_action)
            else:
                # Merge logic if the action already exists (you can customize this)
                existing_action.command = action.command  # Example of merging logic

        local_db.commit()

    except IntegrityError as e:
        print(f"Error merging data: {e}")
    finally:
        seed_db.close()
        local_db.close()

def setup_local_database():
    """Checks and sets up the local database by copying and merging from the seed database."""
    if not os.path.exists(LOCAL_DB_PATH):
        shutil.copy(SEED_DB_PATH, LOCAL_DB_PATH)
    else:
        copy_and_merge_seed_data()

class DatabaseManager:
    def __init__(self, db_type='local'):
        self.db_type = db_type
        self.engine = local_engine if db_type == 'local' else seed_engine
        self.SessionLocal = LocalSessionLocal if db_type == 'local' else SeedSessionLocal

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def store_action(self, action_name, action_type, action_data, command):
        """Stores a user action in the database."""
        try:
            db = next(self.get_db())
            new_action = UserAction(action_name=action_name, action_type=action_type,
                                    action_data=action_data, command=command)
            db.add(new_action)
            db.commit()
        except Exception as e:
            print(f"Error storing action: {e}")
        finally:
            db.close()  # Ensure session is closed even on errors
    def update_action(self, old_name, new_name, new_type, new_data, new_count, new_command):
        try:
            db = next(self.get_db())
            action = db.query(UserAction).filter(UserAction.action_name == old_name).first()
            if action:
                action.action_name = new_name
                action.action_type = new_type
                action.action_data = new_data
                action.pressed_count = new_count
                action.command = new_command
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error updating action: {e}")
            return False
        finally:
            db.close()

    def get_all_actions(self):
        """Retrieves all user actions from the database."""
        try:
            db = next(self.get_db())
            actions = db.query(UserAction).all()
            return actions
        except Exception as e:
            print(f"Error retrieving actions: {e}")
            return []
        finally:
            db.close()

    def get_action_by_name(self, action_name):
        """Retrieves a specific user action by its name."""
        try:
            db = next(self.get_db())
            action = db.query(UserAction).filter(UserAction.action_name == action_name).first()
            
            # Option 1: Access all attributes before closing the session
            if action:
                action_name = action.action_name
                action_type = action.action_type
                action_data = action.action_data
                pressed_count = action.pressed_count
                command = action.command
            
            return action
        except Exception as e:
            print(f"Error retrieving action: {e}")
            return None
        finally:
            db.close()


    def increment_press_count(self, action_name):
        """Increments the press count for a specific action."""
        try:
            db = next(self.get_db())
            action = db.query(UserAction).filter(UserAction.action_name == action_name).first()
            if action:
                action.pressed_count = (action.pressed_count or 0) + 1
                db.commit()
            return action
        except Exception as e:
            print(f"Error incrementing press count: {e}")
            return None
        finally:
            db.close()

    def store_risk(self, risk_data):
        """Stores a risk in the database."""
        try:
            db = next(self.get_db())
            new_risk = Risk(**risk_data)
            db.add(new_risk)
            db.commit()
            return new_risk.id
        except Exception as e:
            logging.error(f"Error storing risk: {e}")
            return None
        finally:
            db.close()

    def get_all_risks(self):
        """Retrieves all risks from the database."""
        try:
            db = next(self.get_db())
            risks = db.query(Risk).all()
            return risks
        except Exception as e:
            logging.error(f"Error retrieving risks: {e}")
            return []
        finally:
            db.close()

    def update_risk(self, risk_id, risk_data):
        """Updates an existing risk in the database."""
        try:
            db = next(self.get_db())
            risk = db.query(Risk).filter(Risk.id == risk_id).first()
            if risk:
                for key, value in risk_data.items():
                    setattr(risk, key, value)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logging.error(f"Error updating risk: {e}")
            return False
        finally:
            db.close()

    def delete_risk(self, risk_id):
        """Deletes a risk from the database."""
        try:
            db = next(self.get_db())
            risk = db.query(Risk).filter(Risk.id == risk_id).first()
            if risk:
                db.delete(risk)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logging.error(f"Error deleting risk: {e}")
            return False
        finally:
            db.close()