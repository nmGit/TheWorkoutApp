import { Navigate, Route, Routes } from 'react-router-dom'
import { NavBar } from './components/NavBar'
import { RestTimerBar } from './components/RestTimerBar'
import { ActiveWorkoutPage } from './pages/ActiveWorkout'
import { ExerciseDetailPage } from './pages/ExerciseDetail'
import { ExerciseLibraryPage } from './pages/ExerciseLibrary'
import { HistoryPage } from './pages/History'
import { HomePage } from './pages/Home'
import { SettingsPage } from './pages/Settings'
import { TemplateEditorPage } from './pages/TemplateEditor'
import { TemplatesPage } from './pages/Templates'
import { WorkoutDetailPage } from './pages/WorkoutDetail'

function App() {
  return (
    <div className="min-h-full pb-24">
      <main className="mx-auto max-w-xl px-4 pt-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/workout/active" element={<ActiveWorkoutPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/templates/:id" element={<TemplateEditorPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:workoutId" element={<WorkoutDetailPage />} />
          <Route path="/exercises" element={<ExerciseLibraryPage />} />
          <Route path="/exercises/:id" element={<ExerciseDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <RestTimerBar />
      <NavBar />
    </div>
  )
}

export default App
