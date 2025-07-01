from webapp import app
from src.database.models import GradingResult, Submission
from flask import jsonify

@app.route('/api/check-db', methods=['GET'])
def check_db():
    try:
        results = GradingResult.query.all()
        submissions = Submission.query.all()
        
        data = {
            'total_grading_results': len(results),
            'total_submissions': len(submissions),
            'sample_result': None,
            'sample_submission': None
        }
        
        if results:
            sample = results[0]
            data['sample_result'] = {
                'id': sample.id,
                'submission_id': sample.submission_id,
                'progress_id': sample.progress_id,
                'created_at': str(sample.created_at)
            }
        
        if submissions:
            sample = submissions[0]
            data['sample_submission'] = {
                'id': sample.id,
                'filename': sample.filename,
                'processing_status': sample.processing_status
            }
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Adding check-db route to the app")
    # The route is now registered with the app
    print("Run the app normally with run_app.py")