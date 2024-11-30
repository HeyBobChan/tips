/* global use, db */
// MongoDB Playground
// To disable this template go to Settings | MongoDB | Use Default Template For Playground.
// Make sure you are connected to enable completions and to be able to run a playground.
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.
// The result of the last command run in a playground is shown on the results panel.
// By default the first 20 documents will be returned with a cursor.
// Use 'console.log()' to print to the debug output.
// For more documentation on playgrounds please refer to
// https://www.mongodb.com/docs/mongodb-vscode/playgrounds/

// Select the database to use.
use('tipsManagementDB');

// Drop existing collections if any
db.workers.drop();
db.dailyEntries.drop();

// Create workers collection and insert data
db.workers.insertOne({
  workers: [
    "איתא",
    "לרה",
    "דדי",
    "עמר",
    "יגר"
  ]
});

// Create schema for daily entries
db.createCollection("dailyEntries", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["date", "employees"],
      properties: {
        date: {
          bsonType: "date",
          description: "Date of the entry"
        },
        totalHours: {
          bsonType: "double",
          description: "Total hours worked"
        },
        totalCashTips: {
          bsonType: "double",
          description: "Total cash tips"
        },
        totalCreditTips: {
          bsonType: "double",
          description: "Total credit tips"
        },
        employees: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["name", "hours"],
            properties: {
              name: {
                bsonType: "string",
                description: "Employee name"
              },
              hours: {
                bsonType: "double",
                description: "Hours worked"
              },
              cashTips: {
                bsonType: "double",
                description: "Cash tips"
              },
              creditTips: {
                bsonType: "double",
                description: "Credit tips"
              },
              compensation: {
                bsonType: "double",
                description: "Compensation amount"
              }
            }
          }
        }
      }
    }
  }
});

// Create indexes
db.dailyEntries.createIndex({ "date": 1 }, { unique: true });
db.dailyEntries.createIndex({ "employees.name": 1 });

// Insert sample daily entry
db.dailyEntries.insertOne({
  date: new Date("2024-03-14"),
  totalHours: 20.5,
  totalCashTips: 1000,
  totalCreditTips: 1500,
  employees: [
    {
      name: "איתא",
      hours: 8.5,
      cashTips: 400,
      creditTips: 600,
      compensation: 0
    },
    {
      name: "לרה",
      hours: 12,
      cashTips: 600,
      creditTips: 900,
      compensation: 0
    }
  ]
});
