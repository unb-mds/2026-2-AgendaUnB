import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext({});

// Domínio institucional exigido para o papel de professor (RF04).
//
// A arroba colada ao domínio é essencial: @aluno.unb.br TAMBÉM
// termina em "unb.br". Sem o @, todo aluno com e-mail institucional
// conseguiria se cadastrar como professor.
//
// Esta verificação aqui é só experiência de uso — avisar o usuário
// antes de ele preencher tudo. A regra de verdade está no banco,
// porque validação de tela qualquer um burla pelo DevTools.
const EMAIL_INSTITUCIONAL = /@unb\.br$/i;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      } else {
        setLoading(false);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      } else {
        setProfile(null);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (userId) => {
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single();

      if (!error && data) {
        setProfile(data);
      }
    } catch (err) {
      console.error('Erro ao buscar perfil:', err);
    } finally {
      setLoading(false);
    }
  };

  // -----------------------------------------------------------
  // Cadastro com e-mail e senha (RF01, RF02, RF04)
  //
  // O nome completo e o papel vão em options.data. É dali que o
  // trigger do banco os lê para criar a linha em profiles. Sem
  // isso, o nome cai para a parte do e-mail antes da arroba e o
  // papel vira 'student'.
  //
  // Retorna { erro } — null em caso de sucesso, string legível
  // caso contrário, para a tela exibir.
  // -----------------------------------------------------------
  const signUpWithEmail = async ({ email, password, nomeCompleto, papel = 'student' }) => {
    const emailLimpo = email.trim().toLowerCase();
    const nomeLimpo = nomeCompleto?.trim() ?? '';

    if (nomeLimpo.length < 2) {
      return { erro: 'Informe seu nome completo.' };
    }

    // Avisa antes de enviar, para o usuário não descobrir só depois
    // de preencher o formulário inteiro.
    if (papel === 'professor' && !EMAIL_INSTITUCIONAL.test(emailLimpo)) {
      return {
        erro: 'Cadastro como professor exige e-mail institucional da UnB (@unb.br). '
            + 'E-mails @aluno.unb.br são de estudante.',
      };
    }

    const { data, error } = await supabase.auth.signUp({
      email: emailLimpo,
      password,
      options: {
        data: {
          nome_completo: nomeLimpo,
          papel,
        },
      },
    });

    if (error) {
      // Quando o trigger do banco recusa o cadastro, o Supabase Auth
      // costuma devolver uma mensagem genérica de erro de banco em
      // vez do texto da exceção. Traduzimos para algo útil.
      const generico = /database error|saving new user/i.test(error.message);
      if (generico && papel === 'professor') {
        return { erro: 'Não foi possível cadastrar como professor. Verifique se o e-mail é @unb.br.' };
      }
      if (/already registered|already exists/i.test(error.message)) {
        return { erro: 'Já existe uma conta com este e-mail.' };
      }
      return { erro: error.message };
    }

    return { erro: null, user: data.user };
  };

  // -----------------------------------------------------------
  // Login com e-mail e senha (RF01)
  // -----------------------------------------------------------
  const signInWithEmail = async ({ email, password }) => {
    const { error } = await supabase.auth.signInWithPassword({
      email: email.trim().toLowerCase(),
      password,
    });

    if (error) {
      if (/invalid login credentials/i.test(error.message)) {
        return { erro: 'E-mail ou senha incorretos.' };
      }
      return { erro: error.message };
    }
    return { erro: null };
  };

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/segunda-pagina`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });
    if (error) console.error('Erro no login com google:', error.message);
  };

  // -----------------------------------------------------------
  // Virar professor depois do cadastro (RF04)
  //
  // Existe porque o login com Google não consegue carregar o papel:
  // o signInWithOAuth não aceita metadata, os dados vêm da conta
  // Google. Então quem entra por ali nasce sempre 'student' e
  // precisa de um segundo passo.
  //
  // A RLS permite o usuário atualizar apenas o próprio perfil, e a
  // constraint do banco recusa se o e-mail não for institucional.
  // -----------------------------------------------------------
  const promoverParaProfessor = async () => {
    if (!user) return { erro: 'Você precisa estar logado.' };

    if (!EMAIL_INSTITUCIONAL.test(user.email ?? '')) {
      return { erro: 'Apenas contas com e-mail @unb.br podem ser de professor.' };
    }

    const { data, error } = await supabase
      .from('profiles')
      .update({ papel: 'professor' })
      .eq('id', user.id)
      .select()
      .single();

    if (error) {
      // 23514 é violação de CHECK: a constraint do banco recusou.
      if (error.code === '23514') {
        return { erro: 'Apenas contas com e-mail @unb.br podem ser de professor.' };
      }
      return { erro: error.message };
    }

    setProfile(data);
    return { erro: null };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        isProfessor: profile?.papel === 'professor',
        isAdmin: profile?.papel === 'admin',
        signUpWithEmail,
        signInWithEmail,
        signInWithGoogle,
        promoverParaProfessor,
        signOut,
      }}
    >
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);