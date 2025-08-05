import logging
from app.database import SessionLocal, create_db_and_tables
from app.models import User, News, Article
from app.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    db = SessionLocal()
    try:
        logger.info("Checking for admin user...")
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.info("Admin user not found. Creating one...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("1234"),
                role="manager"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info("Admin user 'admin' created.")
        else:
            logger.info("Admin user already exists.")

        # 2. Create Member User
        member_user = db.query(User).filter(User.username == "member").first()
        if not member_user:
            logger.info("Member user not found. Creating one...")
            member_user = User(
                username="member",
                email="member@example.com",
                hashed_password=get_password_hash("1234"),
                role="member"
            )
            db.add(member_user)
            db.commit()
            db.refresh(member_user)
            logger.info("Member user 'member' created.")
        else:
            logger.info("Member user already exists.")

        logger.info("Clearing old news and articles...")
        db.query(News).delete()
        db.query(Article).delete()
        db.commit()

        logger.info("Seeding new sample data...")
        news_items = [
            News(title="رویداد بزرگ علمی", summary="بزرگترین رویداد علمی سال با حضور دانشمندان برجسته برگزار خواهد شد.", content="موضوعات اصلی شامل هوش مصنوعی، بیوتکنولوژی و علوم فضایی است.", image_url="https://images.unsplash.com/photo-1581093458791-9a6685a3c2a6?w=800", category="رویدادها", published=True, owner_id=admin_user.id),
            News(title="کشف جدید در پزشکی", summary="محققان موفق به شناسایی یک روش نوین برای درمان بیماری‌های قلبی شدند.", content="این روش که بر پایه سلول‌های بنیادی است، نتایج بسیار امیدوارکننده‌ای در آزمایشات اولیه نشان داده است.", image_url="https://images.unsplash.com/photo-1576091160550-2173dba999ab?w=800", category="پزشکی", published=True, owner_id=admin_user.id),
            News(title="آینده فناوری 5G", summary="چگونه نسل پنجم شبکه‌های موبایل، دنیای ما را متحول خواهد کرد؟", content="فناوری 5G با سرعت بسیار بالا و تأخیر کم، امکانات جدیدی را برای اینترنت اشیاء (IoT) فراهم می‌کند.", image_url="https://images.unsplash.com/photo-1611003221039-9ac5a1e27447?w=800", category="فناوری", published=True, owner_id=admin_user.id)
        ]
        db.add_all(news_items)

        article_items = [
            Article(title="کاربرد هوش مصنوعی در تحلیل داده‌ها", summary="بررسی چگونگی استفاده از الگوریتم‌های یادگیری ماشین برای تحلیل داده‌های حجیم.", content="در این مقاله، الگوریتم‌های مختلفی مانند شبکه‌های عصبی عمیق مورد بررسی قرار گرفته است.", image_url="https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?w=800", published=True, owner_id=admin_user.id),
            Article(title="آینده انرژی‌های تجدیدپذیر", summary="چالش‌ها و فرصت‌های پیش روی توسعه انرژی‌های پاک.", content="این مقاله به بررسی آخرین فناوری‌ها در این زمینه و چشم‌انداز آینده این منابع انرژی می‌پردازد.", image_url="https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?w=800", published=True, owner_id=admin_user.id)
        ]
        db.add_all(article_items)

        db.commit()
        logger.info("Database seeding complete.")

    except Exception as e:
        logger.error(f"An error occurred during database seeding: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Initializing database and tables...")
    create_db_and_tables()
    logger.info("Starting database seeding process...")
    seed_database()
