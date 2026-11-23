	.file	"race.c"
	.text
	.p2align 4
	.type	main._omp_fn.0, @function
main._omp_fn.0:
.LFB24:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rdi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	call	omp_get_num_threads@PLT
	movslq	%eax, %rbp
	call	omp_get_thread_num@PLT
	movslq	%eax, %rcx
	movl	$2000000, %eax
	cqto
	idivq	%rbp
	cmpq	%rdx, %rcx
	jl	.L2
.L5:
	imulq	%rax, %rcx
	addq	%rdx, %rcx
	leaq	(%rax,%rcx), %rdi
	cmpq	%rdi, %rcx
	jge	.L7
	movq	(%rbx), %r8
	movabsq	$5270498306774157605, %r9
	.p2align 4,,10
	.p2align 3
.L4:
	movq	%rcx, %rax
	imulq	%r9
	movq	%rcx, %rax
	sarq	$63, %rax
	sarq	%rdx
	subq	%rax, %rdx
	movq	%rcx, %rax
	incq	%rcx
	leaq	0(,%rdx,8), %rsi
	subq	%rdx, %rsi
	subq	%rsi, %rax
	addq	%rax, %r8
	cmpq	%rcx, %rdi
	jne	.L4
	movq	%r8, (%rbx)
.L7:
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L2:
	.cfi_restore_state
	incq	%rax
	xorl	%edx, %edx
	jmp	.L5
	.cfi_endproc
.LFE24:
	.size	main._omp_fn.0, .-main._omp_fn.0
	.p2align 4
	.type	main._omp_fn.1, @function
main._omp_fn.1:
.LFB25:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushq	%rbx
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	movq	%rdi, %rbx
	subq	$8, %rsp
	.cfi_def_cfa_offset 32
	call	omp_get_num_threads@PLT
	movslq	%eax, %rbp
	call	omp_get_thread_num@PLT
	movslq	%eax, %rcx
	movl	$2000000, %eax
	cqto
	idivq	%rbp
	cmpq	%rdx, %rcx
	jl	.L11
.L14:
	imulq	%rax, %rcx
	xorl	%r8d, %r8d
	addq	%rdx, %rcx
	leaq	(%rax,%rcx), %rdi
	cmpq	%rdi, %rcx
	jge	.L12
	movabsq	$5270498306774157605, %r9
	.p2align 4,,10
	.p2align 3
.L13:
	movq	%rcx, %rax
	imulq	%r9
	movq	%rcx, %rax
	sarq	$63, %rax
	sarq	%rdx
	subq	%rax, %rdx
	movq	%rcx, %rax
	incq	%rcx
	leaq	0(,%rdx,8), %rsi
	subq	%rdx, %rsi
	subq	%rsi, %rax
	addq	%rax, %r8
	cmpq	%rcx, %rdi
	jne	.L13
.L12:
	lock addq	%r8, (%rbx)
	addq	$8, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	popq	%rbx
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L11:
	.cfi_restore_state
	incq	%rax
	xorl	%edx, %edx
	jmp	.L14
	.cfi_endproc
.LFE25:
	.size	main._omp_fn.1, .-main._omp_fn.1
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC0:
	.string	""
.LC1:
	.string	"<-- ERRADO"
.LC2:
	.string	"OK"
.LC3:
	.string	"threads=%d\n"
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC4:
	.string	"sequencial (referencia) = %ld\n"
	.align 8
.LC5:
	.string	"parallel for (corrida)  = %ld   %s\n"
	.align 8
.LC6:
	.string	"com reduction           = %ld   %s\n"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB23:
	.cfi_startproc
	endbr64
	pushq	%r13
	.cfi_def_cfa_offset 16
	.cfi_offset 13, -16
	xorl	%ecx, %ecx
	xorl	%edx, %edx
	leaq	main._omp_fn.0(%rip), %rdi
	pushq	%r12
	.cfi_def_cfa_offset 24
	.cfi_offset 12, -24
	pushq	%rbp
	.cfi_def_cfa_offset 32
	.cfi_offset 6, -32
	pushq	%rbx
	.cfi_def_cfa_offset 40
	.cfi_offset 3, -40
	subq	$24, %rsp
	.cfi_def_cfa_offset 64
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	movq	%rsp, %rbp
	movq	$0, (%rsp)
	movq	%rbp, %rsi
	call	GOMP_parallel@PLT
	movq	%rbp, %rsi
	xorl	%ecx, %ecx
	xorl	%edx, %edx
	leaq	main._omp_fn.1(%rip), %rdi
	movq	(%rsp), %rbx
	movq	$0, (%rsp)
	xorl	%ebp, %ebp
	call	GOMP_parallel@PLT
	movq	(%rsp), %r12
	xorl	%ecx, %ecx
	movabsq	$5270498306774157605, %rsi
	.p2align 4,,10
	.p2align 3
.L21:
	movq	%rcx, %rax
	imulq	%rsi
	movq	%rcx, %rax
	sarq	$63, %rax
	sarq	%rdx
	subq	%rax, %rdx
	leaq	0(,%rdx,8), %rax
	subq	%rdx, %rax
	movq	%rcx, %rdx
	incq	%rcx
	subq	%rax, %rdx
	addq	%rdx, %rbp
	cmpq	$2000000, %rcx
	jne	.L21
	call	omp_get_max_threads@PLT
	leaq	.LC3(%rip), %rsi
	movl	$2, %edi
	leaq	.LC1(%rip), %r13
	movl	%eax, %edx
	xorl	%eax, %eax
	call	__printf_chk@PLT
	movq	%rbp, %rdx
	leaq	.LC4(%rip), %rsi
	movl	$2, %edi
	xorl	%eax, %eax
	call	__printf_chk@PLT
	cmpq	%rbp, %rbx
	leaq	.LC0(%rip), %rcx
	movq	%rbx, %rdx
	cmovne	%r13, %rcx
	leaq	.LC5(%rip), %rsi
	movl	$2, %edi
	xorl	%eax, %eax
	call	__printf_chk@PLT
	cmpq	%rbp, %r12
	leaq	.LC2(%rip), %rax
	movq	%r12, %rdx
	cmovne	%r13, %rax
	leaq	.LC6(%rip), %rsi
	movl	$2, %edi
	movq	%rax, %rcx
	xorl	%eax, %eax
	call	__printf_chk@PLT
	movq	8(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L29
	addq	$24, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 40
	xorl	%eax, %eax
	popq	%rbx
	.cfi_def_cfa_offset 32
	popq	%rbp
	.cfi_def_cfa_offset 24
	popq	%r12
	.cfi_def_cfa_offset 16
	popq	%r13
	.cfi_def_cfa_offset 8
	ret
.L29:
	.cfi_restore_state
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE23:
	.size	main, .-main
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	1f - 0f
	.long	4f - 1f
	.long	5
0:
	.string	"GNU"
1:
	.align 8
	.long	0xc0000002
	.long	3f - 2f
2:
	.long	0x3
3:
	.align 8
4:
