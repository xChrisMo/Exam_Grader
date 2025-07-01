# Import our check_db_route to register the route
import check_db_route

# Then run the app normally
from run_app import app

if __name__ == '__main__':
    print("Starting app with check-db route")
    app.run(debug=True, port=5000)