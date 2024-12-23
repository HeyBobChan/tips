from pymongo import MongoClient
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import sys
from bson import json_util, ObjectId
from pathlib import Path
import pymongo

def load_environment():
    load_dotenv()
    return {
        'uri': os.getenv('MONGODB_URI'),
        'db_name': os.getenv('MONGODB_DB_NAME')
    }

class DatabaseExaminer:
    def __init__(self):
        self.config = load_environment()
        # Connect directly to avoid using MongoService
        self.client = MongoClient(self.config['uri'])
        self.db = self.client[self.config['db_name']]
        self.output_dir = Path(f"db_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.output_dir.mkdir(exist_ok=True)

    def analyze_field_structure(self, documents):
        """Deeply analyze field structure including nested documents and arrays"""
        field_analysis = {}
        
        def analyze_value(value, current_path=""):
            if isinstance(value, dict):
                for k, v in value.items():
                    new_path = f"{current_path}.{k}" if current_path else k
                    analyze_value(v, new_path)
            elif isinstance(value, list):
                if value:  # Only analyze non-empty arrays
                    # Analyze first item as sample
                    new_path = f"{current_path}[]"
                    analyze_value(value[0], new_path)
            else:
                if current_path not in field_analysis:
                    field_analysis[current_path] = {
                        'types': set(),
                        'sample_values': set(),
                        'null_count': 0,
                        'empty_count': 0
                    }
                
                field_analysis[current_path]['types'].add(type(value).__name__)
                
                # Store sample values (limit to 5 unique samples)
                if len(field_analysis[current_path]['sample_values']) < 5:
                    sample_val = str(value)[:100]  # Truncate long values
                    field_analysis[current_path]['sample_values'].add(sample_val)
                
                if value is None:
                    field_analysis[current_path]['null_count'] += 1
                elif value == "":
                    field_analysis[current_path]['empty_count'] += 1

        for doc in documents:
            analyze_value(doc)

        # Convert sets to lists for JSON serialization
        for field_info in field_analysis.values():
            field_info['types'] = list(field_info['types'])
            field_info['sample_values'] = list(field_info['sample_values'])

        return field_analysis

    def get_database_info(self):
        """Get comprehensive information about database structure and contents"""
        database_info = {
            'database_name': self.config['db_name'],
            'collections': {},
            'total_size': 0,
            'export_time': datetime.now().isoformat()
        }

        try:
            collections = self.db.list_collection_names()
            
            for collection_name in collections:
                print(f"\nAnalyzing collection: {collection_name}")
                collection = self.db[collection_name]
                
                # Get collection stats
                stats = self.db.command("collstats", collection_name)
                
                # Get all documents
                documents = list(collection.find())
                doc_count = len(documents)
                
                # Analyze indexes
                indexes = list(collection.list_indexes())
                
                # Analyze field structure
                field_analysis = self.analyze_field_structure(documents)
                
                collection_info = {
                    "document_count": doc_count,
                    "size": stats.get('size', 0),
                    "avg_document_size": stats.get('avgObjSize', 0),
                    "indexes": [
                        {
                            "name": idx.get('name'),
                            "keys": idx.get('key'),
                            "unique": idx.get('unique', False)
                        } for idx in indexes
                    ],
                    "field_analysis": field_analysis
                }
                
                database_info['collections'][collection_name] = collection_info
                database_info['total_size'] += stats.get('size', 0)

                # Export collection data
                data_file = self.output_dir / f"{collection_name}_data.json"
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(documents, f, indent=2, default=json_util.default)
                print(f"Exported {doc_count} documents from {collection_name}")

            # Export database structure information
            structure_file = self.output_dir / "database_structure.json"
            with open(structure_file, 'w', encoding='utf-8') as f:
                json.dump(database_info, f, indent=2, default=str)

            self._print_summary(database_info)
            return True

        except Exception as e:
            print(f"Error during database analysis: {str(e)}")
            return False

    def _print_summary(self, database_info):
        """Print a summary of the database export"""
        print("\nDatabase Export Summary")
        print("=" * 50)
        print(f"Database: {database_info['database_name']}")
        print(f"Export Location: {self.output_dir.absolute()}")
        print(f"Total Collections: {len(database_info['collections'])}")
        print(f"Total Size: {database_info['total_size'] / 1024 / 1024:.2f} MB")
        print("\nCollection Details:")
        print("-" * 50)
        
        for coll_name, coll_info in database_info['collections'].items():
            print(f"\n{coll_name}:")
            print(f"  Documents: {coll_info['document_count']}")
            print(f"  Size: {coll_info['size'] / 1024 / 1024:.2f} MB")
            print(f"  Indexes: {len(coll_info['indexes'])}")
            print(f"  Fields: {len(coll_info['field_analysis'])}")

def main():
    examiner = DatabaseExaminer()
    examiner.get_database_info()

if __name__ == "__main__":
    main()
