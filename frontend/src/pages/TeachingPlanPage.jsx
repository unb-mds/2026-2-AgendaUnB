import { Link } from 'react-router-dom';
import { Icon, ManagementShell } from '../components/ManagementUI';
import { useAuth } from '../contexts/AuthContext';

export default function TeachingPlanPage() {
  const { user } = useAuth();
  return <ManagementShell title="Plano de Ensino" description="Um espaço para organizar os planos de ensino das suas disciplinas.">
    <section className="teaching-plan-empty" aria-labelledby="teaching-plan-status">
      <Icon>description</Icon>
      <h2 id="teaching-plan-status">Esta área está em preparação</h2>
      <p>O envio de PDFs e a extração de avaliações ainda não estão disponíveis. Por enquanto, você pode adicionar provas, trabalhos e outros prazos manualmente à sua agenda.</p>
      <Link className="manage-button primary" to={user ? '/eventos?aba=meus' : '/'}>{user ? 'Organizar meus eventos' : 'Entrar para organizar minha agenda'}<Icon>arrow_forward</Icon></Link>
    </section>
  </ManagementShell>;
}
