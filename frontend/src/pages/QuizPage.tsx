/**
 * Quiz Dashboard Page - Admin view for managing quizzes
 *
 * Features:
 * - List all quizzes created by the user
 * - Create new quizzes from notebooks
 * - View quiz results
 * - Delete quizzes
 */

import { Header } from '../components/Header';
import { MainLayout } from '../components/Layout';
import { QuizDashboard } from '../components/Quiz/admin';

export function QuizPage() {
  return (
    <MainLayout header={<Header />}>
      <QuizDashboard />
    </MainLayout>
  );
}

export default QuizPage;
