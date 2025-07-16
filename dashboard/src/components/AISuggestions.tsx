import React, { useState, useEffect } from 'react';

interface PhaseReview {
  overall_quality: number;
  quality_rating: string;
  key_insights: string[];
  improvement_suggestions: string[];
  problematic_assignments?: string[];
  problematic_teams?: string[];
  strengths: string[];
  confidence: number;
  phase: string;
  review_timestamp: string;
  recommended_changes?: string[];
  recommended_swaps?: string[];
  success_predictions?: string[];
}

interface AIReviewsData {
  reviews: {
    phase1: PhaseReview | null;
    phase2: PhaseReview | null;
    phase3: PhaseReview | null;
  };
  total_reviews: number;
  last_updated: string;
}

const AISuggestions: React.FC = () => {
  const [reviewsData, setReviewsData] = useState<AIReviewsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPhase, setSelectedPhase] = useState<'phase1' | 'phase2' | 'phase3'>('phase3');

  useEffect(() => {
    fetchAIReviews();
  }, []);

  const fetchAIReviews = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/simple/ai-reviews');
      if (!response.ok) {
        throw new Error('Failed to fetch AI reviews');
      }
      const data = await response.json();
      setReviewsData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching AI reviews:', err);
    } finally {
      setLoading(false);
    }
  };

  const getQualityColor = (rating: string) => {
    switch (rating.toLowerCase()) {
      case 'excellent':
        return 'bg-green-100 text-green-800';
      case 'good':
        return 'bg-blue-100 text-blue-800';
      case 'fair':
        return 'bg-yellow-100 text-yellow-800';
      case 'poor':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPhaseTitle = (phase: string) => {
    switch (phase) {
      case 'phase1':
        return 'Phase 1: Participant-Problem Assignments';
      case 'phase2':
        return 'Phase 2: Team Formation';
      case 'phase3':
        return 'Phase 3: Team-Problem Assignments';
      default:
        return 'Unknown Phase';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-lg text-gray-600">Loading AI suggestions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading AI Suggestions</h3>
        <p className="text-red-600">{error}</p>
        <button 
          onClick={fetchAIReviews}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!reviewsData || reviewsData.total_reviews === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="text-lg font-medium text-yellow-800 mb-2">No AI Reviews Available</h3>
        <p className="text-yellow-600">Run the matching phases to generate AI suggestions.</p>
      </div>
    );
  }

  const selectedReview = reviewsData.reviews?.[selectedPhase] || null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">AI Suggestions & Quality Reviews</h2>
        <div className="text-sm text-gray-500">
          Last updated: {reviewsData.last_updated ? new Date(reviewsData.last_updated).toLocaleString() : 'Never'}
        </div>
      </div>

      {/* Phase Selector */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
        {(['phase1', 'phase2', 'phase3'] as const).map((phase) => {
          const review = reviewsData.reviews?.[phase];
          const hasReview = review !== null && review !== undefined;
          
          return (
            <button
              key={phase}
              onClick={() => setSelectedPhase(phase)}
              disabled={!hasReview}
              className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                selectedPhase === phase
                  ? 'bg-white text-blue-600 shadow-sm'
                  : hasReview
                  ? 'text-gray-600 hover:text-gray-900'
                  : 'text-gray-400 cursor-not-allowed'
              }`}
            >
              {getPhaseTitle(phase).split(':')[0]}
              {hasReview && review && (
                <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${getQualityColor(review.quality_rating)}`}>
                  {review.quality_rating}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Review Content */}
      {selectedReview ? (
        <div className="space-y-6">
          {/* Quality Overview */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {getPhaseTitle(selectedReview.phase || selectedPhase)}
              </h3>
              <div className="flex items-center space-x-3">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getQualityColor(selectedReview.quality_rating || 'unknown')}`}>
                  {selectedReview.quality_rating || 'Unknown'}
                </span>
                <div className="text-sm text-gray-500">
                  Quality Score: {((selectedReview.overall_quality || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Quality Bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                <span>Overall Quality</span>
                <span>Confidence: {((selectedReview.confidence || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-600 h-3 rounded-full" 
                  style={{ width: `${(selectedReview.overall_quality || 0) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Key Insights */}
          <div className="bg-white rounded-lg shadow p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Key Insights</h4>
            <ul className="space-y-2">
              {(selectedReview.key_insights || []).map((insight, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <span className="text-blue-500 mt-1">•</span>
                  <span className="text-gray-700">{insight}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Improvement Suggestions */}
          <div className="bg-white rounded-lg shadow p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Improvement Suggestions</h4>
            <ul className="space-y-3">
              {(selectedReview.improvement_suggestions || []).map((suggestion, index) => (
                <li key={index} className="flex items-start space-x-3 p-3 bg-yellow-50 rounded-lg">
                  <span className="text-yellow-500 mt-1">•</span>
                  <span className="text-gray-800">{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Strengths & Issues */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Strengths */}
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="text-lg font-semibold text-green-800 mb-3">Strengths</h4>
              <ul className="space-y-2">
                {(selectedReview.strengths || []).map((strength, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-green-500 mt-1">+</span>
                    <span className="text-gray-700">{strength}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Areas of Concern */}
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="text-lg font-semibold text-red-800 mb-3">Areas of Concern</h4>
              {selectedReview.problematic_assignments && selectedReview.problematic_assignments.length > 0 ? (
                <ul className="space-y-2">
                  {selectedReview.problematic_assignments.map((issue, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-red-500 mt-1">!</span>
                      <span className="text-gray-700">{String(issue)}</span>
                    </li>
                  ))}
                </ul>
              ) : selectedReview.problematic_teams && selectedReview.problematic_teams.length > 0 ? (
                <ul className="space-y-2">
                  {selectedReview.problematic_teams.map((issue, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-red-500 mt-1">!</span>
                      <span className="text-gray-700">
                        {typeof issue === 'object' && issue !== null ? 
                          (issue.team && issue.problem ? 
                            `Team ${issue.team} - Problem: ${issue.problem}` :
                            JSON.stringify(issue)
                          ) : 
                          String(issue || 'Unknown issue')
                        }
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 italic">No significant issues identified</p>
              )}
            </div>
          </div>

          {/* Additional Recommendations */}
          {(selectedReview.recommended_changes || selectedReview.recommended_swaps || selectedReview.success_predictions) && (
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-3">Specific Recommendations</h4>
              
              {selectedReview.recommended_changes && selectedReview.recommended_changes.length > 0 && (
                <div className="mb-4">
                  <h5 className="font-medium text-gray-800 mb-2">Recommended Changes:</h5>
                  <ul className="space-y-1 ml-4">
                    {selectedReview.recommended_changes.map((change, index) => (
                      <li key={index} className="text-gray-700">
                        • {typeof change === 'object' && change !== null ? 
                          (change.team && change.action ? 
                            `Team ${change.team}: ${change.action}` :
                            JSON.stringify(change)
                          ) : 
                          String(change || 'No details available')
                        }
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedReview.recommended_swaps && selectedReview.recommended_swaps.length > 0 && (
                <div className="mb-4">
                  <h5 className="font-medium text-gray-800 mb-2">Recommended Swaps:</h5>
                  <ul className="space-y-1 ml-4">
                    {selectedReview.recommended_swaps.map((swap, index) => (
                      <li key={index} className="text-gray-700">
                        • {typeof swap === 'object' && swap !== null ? 
                          (swap.from && swap.to ? 
                            `Move from ${swap.from} to ${swap.to}` :
                            JSON.stringify(swap)
                          ) : 
                          String(swap || 'No details available')
                        }
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedReview.success_predictions && selectedReview.success_predictions.length > 0 && (
                <div>
                  <h5 className="font-medium text-gray-800 mb-2">Success Predictions:</h5>
                  <ul className="space-y-1 ml-4">
                    {selectedReview.success_predictions.map((prediction, index) => (
                      <li key={index} className="text-gray-700">
                        • {typeof prediction === 'object' && prediction !== null ? 
                          JSON.stringify(prediction) : 
                          String(prediction || 'No prediction available')
                        }
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Refresh Button */}
          <div className="flex justify-center">
            <button 
              onClick={fetchAIReviews}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh AI Reviews
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">No AI review available for {getPhaseTitle(selectedPhase)}</p>
        </div>
      )}
    </div>
  );
};

export default AISuggestions; 