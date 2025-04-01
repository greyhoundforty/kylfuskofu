from app import db
from app.models import YourModel  # Replace with your actual model name
import unittest


class TestModels(unittest.TestCase):
    def setUp(self):
        self.app = db.create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_model_creation(self):
        entry = YourModel(
            field1="value1", field2="value2"
        )  # Replace with actual fields
        db.session.add(entry)
        db.session.commit()
        self.assertIsNotNone(entry.id)

    def test_model_retrieval(self):
        entry = YourModel(
            field1="value1", field2="value2"
        )  # Replace with actual fields
        db.session.add(entry)
        db.session.commit()
        retrieved_entry = YourModel.query.get(entry.id)
        self.assertEqual(retrieved_entry.field1, "value1")  # Replace with actual fields

    def test_model_random_selection(self):
        for i in range(10):
            entry = YourModel(
                field1=f"value{i}", field2="value{i}"
            )  # Replace with actual fields
            db.session.add(entry)
        db.session.commit()
        random_entries = YourModel.query.order_by(func.random()).limit(10).all()
        self.assertEqual(len(random_entries), 10)


if __name__ == "__main__":
    unittest.main()
