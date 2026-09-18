import { useNavigate } from 'react-router-dom'
import { Button, NotFoundState } from '../components'

export function NotFoundPage() {
  const navigate = useNavigate()
  return <NotFoundState action={<Button onClick={() => navigate('/cases')}>Return to cases</Button>} />
}
