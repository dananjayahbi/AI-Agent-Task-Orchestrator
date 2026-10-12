import { CreateProjectForm } from '@/components/projects/create-project-form';

/** Create-project route (MT-4.2-02; FR-PRJ-01 — server assigns the PID). */
export default function NewProjectPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">New project</h1>
        <p className="text-sm text-muted-foreground">
          The project id (PID) is assigned by the server when you create the project.
        </p>
      </div>
      <CreateProjectForm />
    </div>
  );
}
