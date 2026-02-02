/**
 * Quiz Results Page - View results for a specific quiz
 */

import { Header } from '../components/Header';
import { MainLayout } from '../components/Layout';
import { QuizResultsTable } from '../components/Quiz/admin';

export function QuizResultsPage() {
  return (
    <MainLayout header={<Header />}>
      <QuizResultsTable />
    </MainLayout>
  );
}

export default QuizResultsPage;
