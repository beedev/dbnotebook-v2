/**
 * Quiz Create Page - Form to create a new quiz
 */

import { Header } from '../components/Header';
import { MainLayout } from '../components/Layout';
import { QuizConfigForm } from '../components/Quiz/admin';

export function QuizCreatePage() {
  return (
    <MainLayout header={<Header />}>
      <QuizConfigForm />
    </MainLayout>
  );
}

export default QuizCreatePage;
